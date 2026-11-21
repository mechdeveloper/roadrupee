"""SILENT_FAILURE: a resident says the same problem is back, but the repair was never recorded as reopened.

Claude only classifies the posts (ai/social.py, cached JSON). The matching here is deterministic:
a recurrence post whose locality geocodes to a ward is matched to a work order in that ward with the same issue
type, completed within WINDOW_DAYS BEFORE the post, and NOT marked reopened_within_30d. The closest completion wins.
Same ward and issue type is NOT proof of the same road, so these flags are review tier only, never audit.
"""
from __future__ import annotations

import pandas as pd

from ..ai.social import text_hash
from ..ai.store import social_store
from . import trace as T
from .flags import Flag

WINDOW_DAYS = 45
RULE = "SILENT_FAILURE"


def load_posts(pre) -> pd.DataFrame:
    return pd.read_csv(pre.data.dir / "social_posts.csv", parse_dates=["posted_at"])


def match(wo: pd.DataFrame, ward: str, issue: str, posted_at: pd.Timestamp) -> pd.Series | None:
    """The work order this post is most plausibly about, or None."""
    c = wo[(wo.ward_code == ward) & (wo.work_type == issue) & (~wo.reopened)
           & (wo.completed_at <= posted_at) & (wo.completed_at >= posted_at - pd.Timedelta(days=WINDOW_DAYS))]
    if c.empty:
        return None
    return c.sort_values(["completed_at", "work_order_id"]).iloc[-1]  # closest completion before the post


def flags_from(pre, idx: T.TraceIndex, entries: dict) -> list[Flag]:
    """One flag per work order, carrying every post that matched it. Deterministic order."""
    per_wo: dict[str, list[dict]] = {}
    wo_rows: dict[str, pd.Series] = {}
    for p in load_posts(pre).itertuples():
        e = entries.get(p.post_id)
        if not e or e.get("input_hash") != text_hash(p.text):
            continue
        if not (e["is_road_issue"] and e["is_recurrence"]) or e["issue_type"] == "other" or not e["locality"]:
            continue
        geo = T.geocode(e["locality"], idx)
        if not geo:
            continue
        best = match(pre.wo, geo["ward_code"], e["issue_type"], p.posted_at)
        if best is None:
            continue
        wid = best.work_order_id
        wo_rows[wid] = best
        per_wo.setdefault(wid, []).append(dict(
            post_id=p.post_id, posted_at=str(p.posted_at)[:16], source=p.source, text=p.text, language=e["language"],
            locality=geo["locality"], likes_or_forwards=int(p.likes_or_forwards),
            days_after_repair=int((p.posted_at.normalize() - best.completed_at.normalize()).days)))
    out: list[Flag] = []
    for wid in sorted(per_wo):
        r, posts = wo_rows[wid], sorted(per_wo[wid], key=lambda x: x["posted_at"])
        days = posts[0]["days_after_repair"]
        out.append(Flag(
            rule=RULE, tier="review", severity="low", work_order_ids=[wid],
            reason=(f"Resident posts in this ward say the same kind of problem is back, {days} days after this repair "
                    "was finished and recorded as holding. Same ward and issue type, not proven to be the same road: "
                    "worth checking."),
            ward_code=r.ward_code, road_id=r.road_id, contractor_id=r.contractor_id, cost_inr=float(r.cost_inr),
            expected_inr=float(r.expected_cost_inr), amount_inr=float(r.cost_inr), extra={"posts": posts}))
    return out


def build(pre) -> list[Flag]:
    store = social_store()
    if not store.items:  # no classification yet: no silent flags, nothing else changes
        return []
    return flags_from(pre, T.build_index(pre), store.items)
