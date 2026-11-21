"""Ward / contractor / search page endpoints."""
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def wards(client):
    return client.get("/api/wards").json()


def test_slugs_unique_and_url_safe(wards):
    slugs = [w["slug"] for w in wards]
    assert len(slugs) == len(set(slugs)) == 24
    assert all(re.fullmatch(r"[a-z]+(-[a-z]+)?", s) for s in slugs)
    assert next(w for w in wards if w["ward_code"] == "G/S")["slug"] == "g-s"
    assert all(w["localities"] for w in wards)


def test_ward_detail_and_404(client):
    assert client.get("/api/wards/t").json()["ward_code"] == "T"
    assert client.get("/api/wards/nope").status_code == 404


def test_flow_totals_equal_ward_spend(client, wards):
    for w in wards:
        f = client.get(f"/api/wards/{w['slug']}/flow").json()
        assert abs(f["spend_inr"] - w["spend_inr"]) < 1
        assert abs(f["held_inr"] + f["failed_inr"] - f["spend_inr"]) < 1
        assert abs(sum(c["spend_inr"] for c in f["contractors"]) - f["spend_inr"]) < 1
        assert abs(sum(m["failed_inr"] for m in f["methods"]) - f["failed_inr"]) < 1
        n = len(f["nodes"])
        assert all(0 <= l["source"] < n and 0 <= l["target"] < n and l["value"] > 0 for l in f["links"])
        # money in = money out at each contractor and method node
        for i, node in enumerate(f["nodes"]):
            if node["kind"] in ("contractor", "method"):
                inflow = sum(l["value"] for l in f["links"] if l["target"] == i)
                outflow = sum(l["value"] for l in f["links"] if l["source"] == i)
                assert abs(inflow - node["value_inr"]) < 1 and abs(outflow - node["value_inr"]) < 1


def test_timeline_failures_match_ward(client, wards):
    for w in wards:
        t = client.get(f"/api/wards/{w['slug']}/timeline").json()
        assert t["failed_total"] == sum(d["failed"] for d in t["days"])
        assert t["rain_data_ends"] == "2025-09-30"
        assert all(d["rain_mm"] is None for d in t["days"] if d["date"] > t["rain_data_ends"])
        assert any(d["rain_mm"] is not None for d in t["days"])
    assert client.get("/api/wards/t/timeline").json()["red_alert_days"] == 9


def test_timeline_failed_count_equals_reopened_work_orders(client, wards):
    pre = app.state.pre
    for w in wards:
        t = client.get(f"/api/wards/{w['slug']}/timeline").json()
        n = int(((pre.wo.ward_code == w["ward_code"]) & pre.wo.reopened).sum())
        assert t["failed_total"] == n


def test_contractor_card(client):
    r = client.get("/api/contractors/ct03")
    assert r.status_code == 200
    c = r.json()
    assert [g["key"] for g in c["grades"]] == ["speed", "durability", "cost", "volume"]
    assert next(g for g in c["grades"] if g["key"] == "volume")["band"] == "neutral"
    assert all(g["band"] in {"better", "as_expected", "worse"} for g in c["grades"] if g["key"] != "volume")
    assert len(c["summary"].split()) <= 120
    assert not any(b in c["summary"].lower() for b in ("fraud", "scam", "corrupt", "steal"))
    assert client.get("/api/contractors/CT99").status_code == 404


def test_contractor_grades_are_fair_across_all_contractors(client):
    bands = {}
    for i in range(1, 9):
        c = client.get(f"/api/contractors/CT0{i}").json()
        assert len(c["summary"].split()) <= 120
        bands[c["contractor_id"]] = {g["key"]: g["band"] for g in c["grades"]}
    # durability uses the CI rule: the strongest outliers must be called out, the best must be 'better'
    assert bands["CT04"]["durability"] == "worse" and bands["CT05"]["durability"] == "better"


def test_localities_and_flag_by_id(client):
    loc = client.get("/api/localities").json()
    assert len(loc) == 118
    assert any(any("ऀ" <= ch <= "ॿ" for ch in a) for l in loc for a in l["aliases"])
    f = client.get("/api/flags/F0001").json()
    assert f["flag_id"] == "F0001" and f["work_order_ids"]
    assert client.get("/api/flags/f0001").status_code == 200
    assert client.get("/api/flags/F9999").status_code == 404
