"""Hook numbers and scorecard metrics. All arithmetic is here, never in an LLM."""
from __future__ import annotations

import pandas as pd

from ..loader import Data
from .expected import wilson
from .flags import Flag

ROAD_DEFECT_CAUSES = ["Pothole", "Waterlogged road", "Uneven road / open chamber"]


def summary(data: Data, wo: pd.DataFrame, flags: list[Flag]) -> dict:
    total = float(wo.cost_inr.sum())
    failed = float(wo.loc[wo.reopened, "cost_inr"].sum())
    dlp = [f for f in flags if f.rule == "DLP_PAID"]
    dlp_audit = [f for f in dlp if f.tier == "audit"]
    over = [f for f in flags if f.rule == "OVER_RATE"]
    acc = data.accidents[data.accidents.probable_cause.isin(ROAD_DEFECT_CAUSES)]
    return {
        "total_spend_inr": total,
        "failed_spend_inr": failed,
        "failed_pct": failed / total * 100,
        "work_orders": int(len(wo)),
        "failed_work_orders": int(wo.reopened.sum()),
        "dlp_paid_total_inr": sum(f.cost_inr for f in dlp),
        "dlp_paid_total_count": len(dlp),
        "dlp_paid_liable_inr": sum(f.cost_inr for f in dlp_audit),
        "dlp_paid_liable_count": len(dlp_audit),
        "over_rate_excess_inr": sum(f.amount_inr for f in over),
        "over_rate_count": len(over),
        "road_defect_fatal": int((acc.severity == "Fatal").sum()),
        "road_defect_grievous": int((acc.severity == "Grievous").sum()),
        "road_defect_accidents": int(len(acc)),
        "accident_causes": ROAD_DEFECT_CAUSES,
        "flag_counts": flag_counts(flags),
        "synthetic_notice": "All data is synthetic; all contractors are fictional.",
    }


def flag_counts(flags: list[Flag]) -> dict:
    out: dict[str, dict] = {}
    for f in flags:
        d = out.setdefault(f.rule, {"count": 0, "audit": 0, "review": 0, "amount_inr": 0.0})
        d["count"] += 1
        d[f.tier] += 1
        d["amount_inr"] += f.amount_inr
    return out


def _group_card(g: pd.DataFrame) -> dict:
    n = len(g)
    k = int(g.reopened.sum())
    exp = float(g.expected_reopen_p.sum())
    lo, hi = wilson(k, n)
    exp_rate = exp / n
    return {
        "work_orders": n,
        "spend_inr": float(g.cost_inr.sum()),
        "failed_spend_inr": float(g.loc[g.reopened, "cost_inr"].sum()),
        "sla_met_pct": float(g.sla_met.eq("Y").mean() * 100),
        "median_cost_vs_rate": float(g.cost_ratio.median()),
        "reopen_observed_pct": k / n * 100,
        "reopen_expected_pct": exp_rate * 100,
        "reopen_gap_pts": (k / n - exp_rate) * 100,
        "reopen_ci_low_pct": lo * 100,
        "reopen_ci_high_pct": hi * 100,
        # Only "worth checking" when even the CI's low end is above what context predicts
        "worth_checking": bool(lo > exp_rate),
        "avg_rain_week_mm": float(g.rain_week_mm.mean()),
    }


def wards(data: Data, wo: pd.DataFrame, flags: list[Flag]) -> list[dict]:
    out = []
    for w in data.wards.itertuples():
        g = wo[wo.ward_code == w.ward_code]
        card = _group_card(g) if len(g) else {}
        fl = [f for f in flags if f.ward_code == w.ward_code]
        budget = float(w.monsoon_repair_budget_inr_2025)
        spend = card.get("spend_inr", 0.0)
        out.append({
            "ward_code": w.ward_code,
            "ward_name": w.ward_name,
            "zone": w.zone,
            "low_lying_index": float(w.low_lying_index),
            "budget_inr": budget,
            "remaining_budget_inr": budget - spend,
            "failed_pct": (card.get("failed_spend_inr", 0.0) / spend * 100) if spend else 0.0,
            "flags_audit": sum(f.tier == "audit" for f in fl),
            "flags_review": sum(f.tier == "review" for f in fl),
            **card,
        })
    return out


def contractors(data: Data, wo: pd.DataFrame) -> list[dict]:
    out = []
    for c in data.contractors.itertuples():
        g = wo[wo.contractor_id == c.contractor_id]
        if len(g):
            out.append({"contractor_id": c.contractor_id, "contractor_name": c.contractor_name,
                        "wards_active": int(g.ward_code.nunique()), **_group_card(g)})
    return out
