"""Home dashboard aggregates and the /audit list."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_top_flags_one_per_ward_audit_only(client):
    d = client.get("/api/home/top-flags?limit=6").json()
    assert d["total_audit"] == 391
    assert len(d["items"]) == 6
    assert len({i["ward_code"] for i in d["items"]}) == 6
    assert all(i["tier"] == "audit" for i in d["items"])
    amounts = [i["amount_inr"] for i in d["items"]]
    assert amounts == sorted(amounts, reverse=True)
    assert all(i["ward_slug"] and i["contractor_name"] for i in d["items"])


def test_home_contractors(client):
    d = client.get("/api/home/contractors").json()
    assert len(d) == 8
    assert all([g["key"] for g in c["grades"]] == ["speed", "durability", "cost", "volume"] for c in d)


def test_city_monsoon_counts_all_failed_repairs(client):
    t = client.get("/api/home/monsoon").json()
    assert t["ward_code"] == "ALL" and t["failed_total"] == 611
    assert t["failed_total"] == sum(x["failed"] for x in t["days"])
    assert t["red_alert_days"] == 9


def test_methods_add_up(client):
    d = client.get("/api/home/methods").json()
    s = client.get("/api/summary").json()
    assert abs(sum(m["spend_inr"] for m in d) - s["total_spend_inr"]) < 1
    assert abs(sum(m["failed_inr"] for m in d) - s["failed_spend_inr"]) < 1


def test_audit_defaults_and_filters(client):
    d = client.get("/api/audit?limit=5").json()
    assert d["total"] == 391 and len(d["items"]) == 5
    over = client.get("/api/audit?rule=over_rate").json()
    assert over["total"] == 109 and all(i["rule"] == "OVER_RATE" for i in over["items"])
    everything = client.get("/api/audit?tier=all").json()
    assert everything["total"] == len(app.state.pre.flags)
    # facets: rule counts ignore the rule filter itself, so the chips still show alternatives
    assert over["facets"]["rule"]["DOUBLE_BILL"] == 45
    assert sum(over["facets"]["contractor"].values()) == 109


def test_audit_combined_filters(client):
    ward = next(iter(client.get("/api/audit").json()["facets"]["ward"]))
    d = client.get(f"/api/audit?ward={ward}&rule=DLP_PAID&limit=200").json()
    assert all(i["ward_slug"] == ward and i["rule"] == "DLP_PAID" for i in d["items"])
    method = client.get("/api/audit").json()["items"][0]["repair_method"]
    m = client.get("/api/audit", params={"method": method}).json()
    assert m["total"] > 0 and all(i["repair_method"] == method for i in m["items"])
    v = client.get("/api/audit?verdict=none&tier=all").json()
    assert all(i["verdict"] is None for i in v["items"])


def test_audit_csv_matches_filters(client):
    r = client.get("/api/audit.csv?rule=OVER_RATE")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("work_order_id,rule,tier")
    assert len(lines) - 1 == 109 and all(",OVER_RATE," in l for l in lines[1:])
