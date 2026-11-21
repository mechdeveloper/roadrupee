"""Deterministic audit rules. Every flag carries work_order_ids as evidence.

Wording is deliberately fair: reasons say "worth checking", never "fraud".
Claude may later add `review` text to a flag but never alters rule fields.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

import pandas as pd

from ..loader import Data

OVER_RATE_X = 1.5
DOUBLE_BILL_DAYS = 7
SLA_SEVERE_X = 2.0
REPEAT_WINDOW_DAYS = 60

# DLP_PAID: surface defects the original road contractor is liable for
DLP_AUDIT_WORK_TYPES = {"Pothole", "Broken paver blocks", "Road cave-in"}
DLP_AUDIT_METHODS = {
    "Cold mix patch",
    "Hot mix patch",
    "Mastic asphalt",
    "Paver blocks relaid",
    "Excavation, pipeline repair, PQC patch",
}
UTILITY_RE = re.compile(r"MTNL|MGL|utility", re.I)
DLP_REVIEW_REASON = "DLP road, but work not covered by road contractor's liability"

TIER = {
    "OVER_RATE": "audit",
    "DOUBLE_BILL": "audit",
    "DLP_PAID": "audit",  # downgraded to "review" per row, see dlp_flags
    "SLA_BREACH": "review",
    "REPEAT_FAILURE": "review",
}


@dataclass
class Flag:
    rule: str
    tier: str
    severity: str  # high | medium | low
    work_order_ids: list[str]  # primary first
    reason: str
    ward_code: str
    road_id: str
    contractor_id: str
    cost_inr: float
    expected_inr: float | None = None
    amount_inr: float = 0.0  # money at stake (excess, or amount paid)
    flag_id: str = ""
    review: dict | None = field(default=None)  # filled by Claude later
    extra: dict | None = None  # rule-specific evidence (SILENT_FAILURE: the social posts)

    def to_dict(self) -> dict:
        d = asdict(self)
        # flat copies for the table / CSV; empty until a verdict exists. The rule fields are never changed.
        d["claude_verdict"] = (self.review or {}).get("verdict", "")
        d["claude_headline"] = (self.review or {}).get("headline", "")
        return d


def inr(x: float) -> str:
    """Indian digit grouping: ₹2,35,386 (not ₹235,386)."""
    n = int(round(x))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return f"{sign}₹{s}"


def add_expected_cost(data: Data, wo: pd.DataFrame) -> pd.DataFrame:
    rc = data.rate_card.set_index("repair_method")
    rate = wo["repair_method"].map(rc["standard_rate_inr"])
    unit = wo["repair_method"].map(rc["unit"])
    out = wo.copy()
    out["expected_cost_inr"] = rate * out["area_sqm"].where(unit.eq("per sqm"), 1.0)
    out["cost_ratio"] = out["cost_inr"] / out["expected_cost_inr"]
    return out


def _base(r: pd.Series) -> dict:
    return dict(
        ward_code=r.ward_code,
        road_id=r.road_id,
        contractor_id=r.contractor_id,
        cost_inr=float(r.cost_inr),
        expected_inr=float(r.expected_cost_inr),
    )


def over_rate(wo: pd.DataFrame) -> list[Flag]:
    out = []
    for r in wo[wo.cost_ratio > OVER_RATE_X].itertuples():
        s = pd.Series(r._asdict())
        excess = r.cost_inr - r.expected_cost_inr
        out.append(Flag(
            rule="OVER_RATE", tier="audit",
            severity="high" if r.cost_ratio >= 2 else "medium",
            work_order_ids=[r.work_order_id],
            reason=(f"Billed {inr(r.cost_inr)} vs about {inr(r.expected_cost_inr)} expected from the rate card "
                    f"({r.cost_ratio:.1f}×). Normal variation is ±30%, so this is worth checking."),
            amount_inr=float(excess), **_base(s),
        ))
    return out


def double_bill(wo: pd.DataFrame) -> list[Flag]:
    out = []
    for (_, _), g in wo.sort_values("assigned_at").groupby(["road_id", "repair_method"]):
        rows = list(g.itertuples())
        for prev, cur in zip(rows, rows[1:]):
            gap = (cur.assigned_at - prev.assigned_at).total_seconds() / 86400
            if gap < DOUBLE_BILL_DAYS and not cur.linked_complaint_ids:
                s = pd.Series(cur._asdict())
                out.append(Flag(
                    rule="DOUBLE_BILL", tier="audit", severity="high",
                    work_order_ids=[cur.work_order_id, prev.work_order_id],
                    reason=(f"Same road and method ({cur.repair_method}) billed again {gap:.1f} days after "
                            f"{prev.work_order_id}, with no complaint linked. Worth checking."),
                    amount_inr=float(cur.cost_inr), **_base(s),
                ))
    return out


def dlp_tier(row) -> str:
    """'audit' only for surface defects the road contractor is liable for."""
    is_surface = row.work_type in DLP_AUDIT_WORK_TYPES and row.repair_method in DLP_AUDIT_METHODS
    utility = bool(UTILITY_RE.search(str(row.engineer_remark)))
    return "audit" if is_surface and not utility else "review"


def dlp_paid(wo: pd.DataFrame, roads: pd.DataFrame) -> list[Flag]:
    dlp = set(roads.loc[roads.under_dlp.eq("Y"), "road_id"])
    out = []
    for r in wo[wo.road_id.isin(dlp) & (wo.cost_inr > 0)].itertuples():
        s = pd.Series(r._asdict())
        tier = dlp_tier(r)
        if tier == "audit":
            sev = "high" if r.cost_ratio > OVER_RATE_X else "medium"
            reason = (f"Road is still under the original contractor's Defect Liability Period, yet BMC paid "
                      f"{inr(r.cost_inr)} for a surface repair ({r.work_type}). Worth checking.")
        else:
            sev = "low"
            reason = DLP_REVIEW_REASON + f" ({r.work_type}; {r.repair_method})."
            if UTILITY_RE.search(str(r.engineer_remark)):
                reason += " Remark mentions a utility trench."
        out.append(Flag(rule="DLP_PAID", tier=tier, severity=sev, work_order_ids=[r.work_order_id],
                        reason=reason, amount_inr=float(r.cost_inr), **_base(s)))
    return out


def sla_breach(data: Data, wo: pd.DataFrame) -> list[Flag]:
    first = data.complaints.set_index("complaint_id")["received_at"]

    def first_complaint(ids: str):
        ts = [first[i] for i in ids.split("|") if i in first.index]
        return min(ts) if ts else pd.NaT

    start = wo["linked_complaint_ids"].map(first_complaint).fillna(wo["assigned_at"])
    hours = (wo["completed_at"] - start).dt.total_seconds() / 3600
    ratio = hours / wo["sla_hours"]
    out = []
    for r, h, x in zip(wo.itertuples(), hours, ratio):
        if x > SLA_SEVERE_X:
            s = pd.Series(r._asdict())
            out.append(Flag(
                rule="SLA_BREACH", tier="review", severity="medium" if x > 3 else "low",
                work_order_ids=[r.work_order_id],
                reason=(f"Completed in {h:.0f} h against a {r.sla_hours} h target ({x:.1f}× the target). "
                        f"Rain delays or access issues may explain it."),
                amount_inr=0.0, **_base(s),
            ))
    return out


def repeat_failure(wo: pd.DataFrame) -> list[Flag]:
    """Same road + same contractor + same repair method, with >=2 reopened WOs whose
    completion dates chain within REPEAT_WINDOW_DAYS of each other. One flag per chain;
    the most recent WO is primary, earlier ones follow as evidence."""
    out = []
    failed = wo[wo.reopened].sort_values("completed_at")
    for (road, contractor, method), g in failed.groupby(["road_id", "contractor_id", "repair_method"]):
        if len(g) < 2:
            continue
        chains: list[list[int]] = [[0]]
        for i in range(1, len(g)):
            gap = (g.completed_at.iloc[i] - g.completed_at.iloc[i - 1]).days
            if gap <= REPEAT_WINDOW_DAYS:
                chains[-1].append(i)
            else:
                chains.append([i])
        for ch in chains:
            if len(ch) < 2:
                continue
            c = g.iloc[ch].sort_values("completed_at", ascending=False)
            s = c.iloc[0]
            out.append(Flag(
                rule="REPEAT_FAILURE", tier="review", severity="medium",
                work_order_ids=list(c.work_order_id),
                reason=(f"Same fix by same contractor failed again within {REPEAT_WINDOW_DAYS} days "
                        f"({len(ch)} reopened jobs on {road}, {method})."),
                ward_code=s.ward_code, road_id=road, contractor_id=contractor,
                cost_inr=float(c.cost_inr.sum()), expected_inr=float(c.expected_cost_inr.sum()),
                amount_inr=float(c.cost_inr.sum()),
            ))
    return out


def run_all(data: Data, wo: pd.DataFrame) -> list[Flag]:
    """wo must already have expected_cost_inr, cost_ratio, expected_reopen_p."""
    flags = (over_rate(wo) + double_bill(wo) + dlp_paid(wo, data.roads)
             + sla_breach(data, wo) + repeat_failure(wo))
    for i, f in enumerate(flags, 1):
        f.flag_id = f"F{i:04d}"
    return flags
