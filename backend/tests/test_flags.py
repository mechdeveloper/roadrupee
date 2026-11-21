"""Regression tests: pin the flag counts so rule changes are deliberate."""
import pytest

from app import cache


@pytest.fixture(scope="module")
def pre():
    return cache.build()


def by_rule(pre, rule, tier=None):
    return [f for f in pre.flags if f.rule == rule and (tier is None or f.tier == tier)]


def test_hook_numbers(pre):
    s = pre.summary
    assert s["work_orders"] == 2499
    assert round(s["total_spend_inr"] / 1e7, 2) == 13.43
    assert round(s["failed_spend_inr"] / 1e7, 2) == 3.07
    assert round(s["failed_pct"]) == 23
    assert s["road_defect_fatal"] == 10


def test_over_rate(pre):
    fl = by_rule(pre, "OVER_RATE")
    assert len(fl) == 109
    assert all(f.cost_inr / f.expected_inr > 1.5 for f in fl)
    assert all(f.tier == "audit" for f in fl)


def test_double_bill(pre):
    fl = by_rule(pre, "DOUBLE_BILL")
    assert len(fl) == 45
    # evidence: later WO first, plus the earlier one
    assert all(len(f.work_order_ids) == 2 for f in fl)
    # the later WO has no linked complaint
    wo = pre.wo.set_index("work_order_id")
    assert all(wo.loc[f.work_order_ids[0], "linked_complaint_ids"] == "" for f in fl)


def test_dlp_paid_before_and_after_tiering(pre):
    allf = by_rule(pre, "DLP_PAID")
    audit = by_rule(pre, "DLP_PAID", "audit")
    review = by_rule(pre, "DLP_PAID", "review")
    # before tiering: every paid WO on a DLP road
    assert len(allf) == 493
    assert round(sum(f.cost_inr for f in allf) / 1e7, 2) == 2.62
    # after tiering: surface defects only are 'audit'
    assert len(audit) == 237
    assert round(sum(f.cost_inr for f in audit) / 1e7, 2) == 0.77
    assert len(review) == 256
    assert round(sum(f.cost_inr for f in review) / 1e7, 2) == 1.85
    assert len(audit) + len(review) == len(allf)


def test_dlp_audit_tier_is_only_liable_surface_work(pre):
    wo = pre.wo.set_index("work_order_id")
    for f in by_rule(pre, "DLP_PAID", "audit"):
        r = wo.loc[f.work_order_ids[0]]
        assert r.work_type in {"Pothole", "Broken paver blocks", "Road cave-in"}
        remark = str(r.engineer_remark)  # blank remarks load as NaN
        assert "MTNL" not in remark and "MGL" not in remark
    for f in by_rule(pre, "DLP_PAID", "review"):
        assert "not covered by road contractor's liability" in f.reason


def test_sla_breach_only_severe(pre):
    fl = by_rule(pre, "SLA_BREACH")
    assert len(fl) == 488
    assert all(f.tier == "review" for f in fl)


def test_repeat_failure(pre):
    fl = by_rule(pre, "REPEAT_FAILURE")
    assert len(fl) == 30
    assert len({w for f in fl for w in f.work_order_ids}) == 63
    assert all(f.tier == "review" for f in fl)
    wo = pre.wo.set_index("work_order_id")
    for f in fl:
        rows = wo.loc[f.work_order_ids]
        assert rows.reopened.all()
        assert rows.road_id.nunique() == rows.contractor_id.nunique() == rows.repair_method.nunique() == 1
        assert f.reason.startswith("Same fix by same contractor failed again within 60 days")


def test_every_flag_has_evidence_and_fair_wording(pre):
    banned = ("fraud", "scam", "corrupt", "steal")
    for f in pre.flags:
        assert f.work_order_ids and f.work_order_ids[0].startswith("WO25-")
        assert f.severity in {"high", "medium", "low"}
        assert not any(b in f.reason.lower() for b in banned)


def test_scorecard_has_context(pre):
    for c in pre.contractors:
        assert 0 <= c["reopen_expected_pct"] <= 100
        assert c["reopen_ci_low_pct"] <= c["reopen_observed_pct"] <= c["reopen_ci_high_pct"]
