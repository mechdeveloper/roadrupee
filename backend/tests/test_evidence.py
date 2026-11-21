"""Evidence pack: one flag of each rule, deterministic, no LLM."""
import pytest
from fastapi.testclient import TestClient

from app.engine import evidence
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def flags(client):
    return client.get("/api/flags?limit=5000").json()["items"]


def first(flags, rule, tier=None):
    return next(f for f in flags if f["rule"] == rule and (tier is None or f["tier"] == tier))


CASES = [("OVER_RATE", None), ("DOUBLE_BILL", None), ("DLP_PAID", "audit"),
         ("DLP_PAID", "review"), ("SLA_BREACH", None), ("REPEAT_FAILURE", None)]


@pytest.mark.parametrize("rule,tier", CASES)
def test_evidence_for_each_rule(client, flags, rule, tier):
    f = first(flags, rule, tier)
    r = client.get(f"/api/flags/{f['flag_id']}/evidence")
    assert r.status_code == 200
    ev = r.json()
    # the rule result is never altered by the evidence pack
    assert ev["rule"] == f["rule"] and ev["tier"] == f["tier"] and ev["claim"] == f["reason"]
    assert ev["work_order_ids"] == f["work_order_ids"]
    assert ev["how_we_checked"]
    assert len(ev["work_orders"]) == len(f["work_order_ids"])
    assert ev["work_orders"][0]["sla_hours"] > 0
    assert ev["road"]["road_name"]
    assert ev["contractor"]["work_orders"] > 0
    assert any("synthetic" in n for n in ev["data_notes"])
    rain = ev["context"]["rain"]
    assert len(rain["window"]) == 15
    assert set(rain["week_before_mm"]) == {"Santacruz", "Colaba"}  # both stations
    assert rain["covered_until"] == "2025-09-30"


def test_rate_check_maths(client, flags):
    f = first(flags, "OVER_RATE")
    rc = client.get(f"/api/flags/{f['flag_id']}/evidence").json()["rate_check"]
    mult = rc["area_sqm"] if rc["unit"] == "per sqm" else 1
    assert rc["expected_inr"] == pytest.approx(rc["standard_rate_inr"] * mult, abs=0.01)
    assert rc["ratio"] == pytest.approx(rc["billed_inr"] / rc["expected_inr"], abs=0.01)
    assert rc["ratio"] > 1.5 and rc["normal_range_pct"] == [20, 30]
    assert len(rc["steps"]) == 3


def test_double_bill_has_pair_and_no_complaint(client, flags):
    f = first(flags, "DOUBLE_BILL")
    ev = client.get(f"/api/flags/{f['flag_id']}/evidence").json()
    primary = f["work_order_ids"][0]
    assert not [c for c in ev["complaints"] if c["work_order_id"] == primary]
    assert ev["complaints_note"] == "No complaint linked"
    assert f["work_order_ids"][1] in [w["work_order_id"] for w in ev["related_work_orders"]]


def test_repeat_failure_chain(client, flags):
    f = first(flags, "REPEAT_FAILURE")
    ev = client.get(f"/api/flags/{f['flag_id']}/evidence").json()
    assert len(ev["work_orders"]) >= 2 and all(w["reopened_within_30d"] for w in ev["work_orders"])
    assert ev["related_work_orders"]


def test_dlp_audit_warranty(client, flags):
    f = first(flags, "DLP_PAID", "audit")
    w = client.get(f"/api/flags/{f['flag_id']}/evidence").json()["context"]["warranty"]
    assert w["under_dlp"] == "Y" and not w["utility_trench_in_remark"]


def test_unknown_flag_404(client):
    assert client.get("/api/flags/F9999/evidence").status_code == 404


def test_hash_is_stable_and_ignores_review(client, flags):
    f = first(flags, "OVER_RATE")
    a = client.get(f"/api/flags/{f['flag_id']}/evidence").json()
    b = client.get(f"/api/flags/{f['flag_id']}/evidence").json()
    assert evidence.evidence_hash(a) == evidence.evidence_hash(b)
    b["claude_review"] = {"verdict": "worth_checking"}
    assert evidence.evidence_hash(a) == evidence.evidence_hash(b)
