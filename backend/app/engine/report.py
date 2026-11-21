"""Sanity-check printout: python -m app.engine.report"""
from __future__ import annotations

from .. import cache
from .flags import inr


def main() -> None:
    pre = cache.build()
    s = pre.summary
    print(f"Work orders: {s['work_orders']}   total spend {inr(s['total_spend_inr'])}")
    print(f"Failed within 30d: {s['failed_work_orders']} WOs, {inr(s['failed_spend_inr'])} ({s['failed_pct']:.1f}%)\n")
    print(f"{'rule':<16}{'total':>7}{'audit':>7}{'review':>8}{'₹ at stake':>18}")
    for rule, d in s["flag_counts"].items():
        print(f"{rule:<16}{d['count']:>7}{d['audit']:>7}{d['review']:>8}{inr(d['amount_inr']):>18}")
    print()
    print(f"DLP_PAID BEFORE tiering: {s['dlp_paid_total_count']} WOs, {inr(s['dlp_paid_total_inr'])}")
    dlp = [f for f in pre.flags if f.rule == "DLP_PAID"]
    for tier in ("audit", "review"):
        t = [f for f in dlp if f.tier == tier]
        print(f"DLP_PAID AFTER  tier={tier:<6}: {len(t)} WOs, {inr(sum(f.cost_inr for f in t))}")
    print(f"\nOVER_RATE excess above rate card: {inr(s['over_rate_excess_inr'])}")
    print(f"Fatal road-defect accidents: {s['road_defect_fatal']} (grievous {s['road_defect_grievous']})")
    worth = [c for c in pre.contractors if c["worth_checking"]]
    print(f"Contractors with reopen CI above expected: {len(worth)} of {len(pre.contractors)}")
    for c in pre.contractors:
        print(f"  {c['contractor_id']} obs {c['reopen_observed_pct']:.1f}% vs exp {c['reopen_expected_pct']:.1f}% "
              f"CI[{c['reopen_ci_low_pct']:.1f},{c['reopen_ci_high_pct']:.1f}] n={c['work_orders']}")


if __name__ == "__main__":
    main()
