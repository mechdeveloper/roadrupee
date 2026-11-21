"""Planner, linker and trace: pin the behaviour so changes are deliberate."""
import pytest

from app import cache
from app.engine.linker import classify, detect_language
from app.engine.trace import trace


@pytest.fixture(scope="module")
def pre():
    return cache.build()


def t(pre, text):
    return trace(text, pre.data, pre.wo, pre.flags, pre.complaints, pre.plan, use_claude=False)


def test_linker_beats_citizen_category(pre):
    a = pre.linker_accuracy
    assert a["checked"] == 4948
    assert a["issue_type_pct"] >= 95 and a["issue_type_pct"] > a["citizen_category_pct"] + 10
    assert a["ward_pct"] >= 95


def test_classify_signals():
    assert classify("x", "Uncovered manhole with a stick and plastic bag as warning") == ("Open or broken manhole", "photo")
    assert classify("Caller reports road cave-in at Sion, near X on Y Road.", None, "1916 Helpline")[0] == "Road cave-in"
    assert classify("रस्त्यावर मोठा खड्डा आहे")[0] == "Pothole"
    assert detect_language("Andheri Kurla Road वर गटाराचे झाकण उघडे आहे") == "mr"
    assert detect_language("Hindmata mein paani bhar gaya") == "hi-en"


def test_plan_matches_contract_for_every_ward(pre):
    from app.contracts.plan import PlanResponse

    assert len(pre.plan["by_ward"]) == 24
    for slug, d in pre.plan["by_ward"].items():
        p = PlanResponse.model_validate(d)
        assert p.ward_slug == slug and 1 <= len(p.items) <= 15
        assert [i.rank for i in p.items] == list(range(1, len(p.items) + 1))
        risks = [i.risk_score for i in p.items]
        assert risks == sorted(risks, reverse=True)
        for i in p.items:
            assert abs(sum(x.points for x in i.score_parts) - i.risk_score) < 0.01
            assert all(x.points <= x.max_points for x in i.score_parts)
            assert i.evidence.complaint_ids  # every item comes from open complaints


def test_plan_top_of_fs_and_durable_methods(pre):
    fs = pre.plan["by_ward"]["f-s"]["items"]
    assert fs[0]["road_name"] == "Dr Babasaheb Ambedkar Road"
    kinds = {r["kind"] for r in fs[0]["reasons"]}
    assert {"flood_hotspot", "ambulance_route", "open_complaints"} <= kinds
    rc = set(pre.data.rate_card.repair_method)
    for d in pre.plan["by_ward"].values():
        for i in d["items"]:
            m = i["recommended_method"]
            assert m["repair_method"] in rc
            assert all(a["reopen_rate_pct"] >= m["reopen_rate_pct"] for a in i["alternatives"])  # most durable, not cheapest


def test_plan_budget_fit_is_greedy(pre):
    for d in pre.plan["by_ward"].values():
        left = d["remaining_inr"]
        for i in d["items"]:
            free = i["cost_basis"].startswith("₹0 to the city")
            if free:
                assert i["estimated_cost_inr"] == 0
            if free:
                assert i["within_budget"]
            elif i["estimated_cost_inr"] <= left:
                assert i["within_budget"]
                left -= i["estimated_cost_inr"]
            else:
                assert not i["within_budget"]


def test_trace_by_id_fixed(pre):
    r = t(pre, "what happened to BMC25-000005?")
    assert r["work_order"]["work_order_id"] == "WO25-00002"
    assert r["steps"] and r["summary"].startswith("Fixed by")


def test_trace_by_id_open(pre):
    r = t(pre, "BMC25-000011")
    assert r["work_order"] is None and r["plan"]["ward_code"] == "H/E"


def test_trace_free_text_marathi(pre):
    r = t(pre, "Andheri Kurla Road वर गटाराचे झाकण उघडे आहे")
    assert r["understood"]["issue_type"] == "Open or broken manhole"
    assert r["understood"]["road_name"] == "Andheri Kurla Road"
    assert r["understood"]["language"] == "mr"


def test_trace_unknown_id(pre):
    assert t(pre, "BMC25-999999")["found"] is False


def test_recommended_set_fits_the_budget_bar(pre):
    """The UI pre-selects within_budget items and sums estimated_cost_inr against max(remaining, 0)."""
    for d in pre.plan["by_ward"].values():
        chosen = sum(i["estimated_cost_inr"] for i in d["items"] if i["within_budget"])
        assert chosen <= max(d["remaining_inr"], 0) + 1e-6, d["ward_slug"]

