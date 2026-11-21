"""SILENT_FAILURE: classifier batching/caching (mocked), deterministic matcher, and no collateral damage."""
import asyncio

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.ai import precompute_social, social
from app.ai.store import JsonStore
from app.contracts.evidence import FlagEvidence
from app.engine import flags as F
from app.engine import silent
from app.engine import trace as T
from app.main import app

BANNED = ("fraud", "scam", "corrupt", "steal", "theft", "bribe")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def pre(client):
    return app.state.pre


# ------------------------------------------------------------------ matcher on small synthetic frames
def wo_frame(rows):
    df = pd.DataFrame(rows)
    df["completed_at"] = pd.to_datetime(df["completed_at"])
    return df


BASE = dict(ward_code="E", work_type="Waterlogging", reopened=False)
POST = pd.Timestamp("2025-08-20 12:00")


def test_window_is_45_days_before_the_post_inclusive():
    wo = wo_frame([
        dict(work_order_id="A", completed_at="2025-07-06 12:00", **BASE),  # exactly 45 days before: in
        dict(work_order_id="B", completed_at="2025-07-05 11:00", **BASE),  # 45 days + 1 h: out
    ])
    assert silent.match(wo, "E", "Waterlogging", POST).work_order_id == "A"
    assert silent.match(wo[wo.work_order_id == "B"], "E", "Waterlogging", POST) is None


def test_each_exclusion():
    ok = dict(work_order_id="A", completed_at="2025-08-10 09:00", **BASE)
    assert silent.match(wo_frame([ok]), "E", "Waterlogging", POST).work_order_id == "A"
    assert silent.match(wo_frame([{**ok, "reopened": True}]), "E", "Waterlogging", POST) is None  # already known failure
    assert silent.match(wo_frame([{**ok, "work_type": "Pothole"}]), "E", "Waterlogging", POST) is None  # other issue
    assert silent.match(wo_frame([{**ok, "ward_code": "T"}]), "E", "Waterlogging", POST) is None  # other ward
    assert silent.match(wo_frame([{**ok, "completed_at": "2025-08-21 09:00"}]), "E", "Waterlogging", POST) is None  # after the post


def test_closest_completion_before_the_post_wins():
    wo = wo_frame([
        dict(work_order_id="OLD", completed_at="2025-07-15 09:00", **BASE),
        dict(work_order_id="NEW", completed_at="2025-08-12 09:00", **BASE),
        dict(work_order_id="MID", completed_at="2025-08-01 09:00", **BASE),
    ])
    assert silent.match(wo, "E", "Waterlogging", POST).work_order_id == "NEW"


# ------------------------------------------------------------------ flags from classified posts
def one_not_reopened_wo(pre):
    w = pre.wo[~pre.wo.reopened & (pre.wo.work_type == "Waterlogging")].iloc[0]
    return w


def test_flags_from_classified_posts(pre, monkeypatch):
    w0 = one_not_reopened_wo(pre)
    idx = T.build_index(pre)
    # two posts a minute apart, right after this repair, so it is the closest completion for both
    t1 = w0.completed_at + pd.Timedelta(minutes=1)
    t2 = w0.completed_at + pd.Timedelta(minutes=2)
    w = silent.match(pre.wo, w0.ward_code, w0.work_type, t1)  # the matcher's own choice is the expectation
    assert silent.match(pre.wo, w0.ward_code, w0.work_type, t2).work_order_id == w.work_order_id
    loc = next(r.locality for r in pre.data.localities.itertuples() if r.ward_code == w.ward_code)
    posts = pd.DataFrame([
        dict(post_id="P1", posted_at=t1, source="X (Twitter)", author_handle="a", text="paani phir se bhar gaya", has_media="N", likes_or_forwards=5),
        dict(post_id="P2", posted_at=t2, source="WhatsApp ALM group", author_handle="b", text="same story again", has_media="N", likes_or_forwards=9),
        dict(post_id="P3", posted_at=t1, source="X (Twitter)", author_handle="c", text="thanks for fixing", has_media="N", likes_or_forwards=1),
    ])
    monkeypatch.setattr(silent, "load_posts", lambda _pre: posts)

    def entry(text, **kw):
        base = dict(input_hash=social.text_hash(text), is_road_issue=True, is_recurrence=True, language="hi-en",
                    locality=loc, issue_type="Waterlogging")
        return {**base, **kw}

    entries = {
        "P1": entry("paani phir se bhar gaya"),
        "P2": entry("same story again", language="en"),
        "P3": entry("thanks for fixing", is_recurrence=False),  # a thank-you is not a recurrence
    }
    out = silent.flags_from(pre, idx, entries)
    assert len(out) == 1  # one flag per work order, carrying both posts
    f = out[0]
    assert f.rule == "SILENT_FAILURE" and f.tier == "review" and f.work_order_ids == [w.work_order_id]
    assert [p["post_id"] for p in f.extra["posts"]] == ["P1", "P2"]
    assert [p["days_after_repair"] for p in f.extra["posts"]] == [0, 0] and f.extra["posts"][1]["likes_or_forwards"] == 9
    assert "worth checking" in f.reason.lower() and not any(b in f.reason.lower() for b in BANNED)
    # a stale cache entry (the post text changed since it was classified) is ignored, never trusted
    entries["P1"]["input_hash"] = "stale"
    entries["P2"]["input_hash"] = "stale"
    assert silent.flags_from(pre, idx, entries) == []


# ------------------------------------------------------------------ classifier: batching, validation, cache
def test_classifier_batches_validates_and_caches(pre, tmp_path, monkeypatch):
    calls = []

    async def fake(client, model, batch, localities):
        calls.append(len(batch))
        outs = [social.PostOut(post_id=p["post_id"], is_road_issue=True, is_recurrence=True, language="en",
                               locality="Atlantis", issue_type="Pothole") for p in batch[:-1]]  # drops the last post
        return social.BatchOut(posts=outs)

    monkeypatch.setattr(social, "classify_batch", fake)
    store = JsonStore(tmp_path / "social.json")
    s1 = asyncio.run(precompute_social.run(pre, object(), "m", store))
    n = s1["posts"]
    assert max(calls) <= social.BATCH and sum(calls) == n
    assert s1["classified"] == n - len(calls)  # one dropped per batch
    assert all(e["locality"] is None for e in store.items.values())  # unknown place names are never trusted
    # second run: everything classified is skipped (cache by text hash); only the dropped posts are retried
    calls.clear()
    s2 = asyncio.run(precompute_social.run(pre, object(), "m", store))
    assert s2["skipped"] == s1["classified"] and s2["classified"] < s1["classified"]


# ------------------------------------------------------------------ nothing else moved
def test_existing_flags_are_untouched_and_silent_ones_are_review_only(pre):
    base = F.run_all(pre.data, pre.wo)
    assert [(f.flag_id, f.rule, f.tier, f.work_order_ids) for f in pre.flags[: len(base)]] == \
           [(f.flag_id, f.rule, f.tier, f.work_order_ids) for f in base]
    silent_flags = pre.flags[len(base):]
    assert all(f.rule == "SILENT_FAILURE" and f.tier == "review" for f in silent_flags)
    assert all(int(f.flag_id[1:]) > len(base) for f in silent_flags)
    counts = {}
    for f in pre.flags:
        counts[f.rule] = counts.get(f.rule, 0) + 1
    assert (counts["OVER_RATE"], counts["DOUBLE_BILL"], counts["DLP_PAID"], counts["SLA_BREACH"], counts["REPEAT_FAILURE"]) == (109, 45, 493, 488, 30)
    assert sum(f.tier == "audit" for f in pre.flags) == 391


def test_cached_verdicts_and_ward_summaries_still_attach(pre):
    # adding the evidence field and the new rule must not invalidate any stored Claude output
    assert sum(1 for f in pre.flags if f.tier == "audit" and f.review is not None) == 391
    assert sum(1 for w in pre.wards if w.get("ai_summary")) == 24


def test_silent_flag_evidence_endpoint(client, pre):
    sf = [f for f in pre.flags if f.rule == "SILENT_FAILURE"]
    if not sf:
        pytest.skip("no silent flags (post classification not present)")
    d = client.get(f"/api/flags/{sf[0].flag_id}/evidence").json()
    FlagEvidence.model_validate(d)
    assert d["social_posts"] and d["social_posts"][0]["text"] and d["tier"] == "review"
    # ordinary flags carry no posts
    other = client.get("/api/flags/F0001/evidence").json()
    assert other["social_posts"] == []
