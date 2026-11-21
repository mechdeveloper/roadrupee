"""GET /api/trail-summary (funnel from the data) and GET /api/plan.csv."""
import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_trail_funnel_adds_up_and_matches_data(client):
    d = client.get("/api/trail-summary").json()
    pre = app.state.pre
    assert d["total"] == len(pre.data.complaints)
    assert d["unique"] == d["total"] - d["duplicates"]
    assert d["held"] + d["failed"] == d["linked"]
    # everything that is not a duplicate ends in exactly one outcome
    assert d["linked"] + d["open_or_in_progress"] + d["forwarded"] + d["rejected"] == d["unique"]
    assert d["duplicates"] == int((pre.data.complaints.status == "Closed - Duplicate").sum())
    assert d["failed"] > 0 and d["held"] > d["failed"]


def test_plan_csv_one_row_per_ward_item(client):
    r = client.get("/api/plan.csv")
    assert r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    plans = app.state.pre.plans.values()
    assert len(rows) == sum(len(p["items"]) for p in plans) > 100
    assert list(rows[0])[:6] == ["ward_code", "rank", "road_id", "road_name", "segment_no", "risk_score"]
    for k in ("complaints", "flood", "traffic", "accidents", "facilities"):
        assert f"{k}_points" in rows[0]
    assert {"recommended_method", "estimated_cost_inr", "within_budget"} <= set(rows[0])
    for row in rows:  # risk score equals the sum of the parts
        s = sum(float(row[f"{k}_points"]) for k in ("complaints", "flood", "traffic", "accidents", "facilities"))
        assert abs(s - float(row["risk_score"])) < 0.2
