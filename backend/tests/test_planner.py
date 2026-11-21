"""Next-rupee engine: every ward's plan obeys the contract and the rules in engine/planner.py."""
import pytest
from fastapi.testclient import TestClient

from app.contracts.plan import CityPlanResponse, PlanResponse
from app.engine import planner
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def pre(client):
    return app.state.pre


def served(client, slug):
    r = client.get("/api/plan", params={"ward": slug})
    assert r.status_code == 200
    return r.json()


def test_every_ward_validates_against_the_contract(client, pre):
    assert len(pre.plans) == 24
    for slug in pre.plans:
        p = PlanResponse.model_validate(served(client, slug))
        assert p.items, slug
        assert [i.rank for i in p.items] == list(range(1, len(p.items) + 1))
        assert 5 <= len(p.items) <= 12 or len(p.items) < 12


def test_formula_and_score_parts(client, pre):
    for slug in pre.plans:
        p = served(client, slug)
        assert sum(w["weight"] for w in p["formula"]["weights"]) == 100
        w = {x["key"]: x["weight"] for x in p["formula"]["weights"]}
        for it in p["items"]:
            assert 0 < it["risk_score"] <= 100
            assert abs(sum(x["points"] for x in it["score_parts"]) - it["risk_score"]) < 0.01
            assert all(x["points"] <= x["max_points"] == w[x["key"]] for x in it["score_parts"])
        scores = [i["risk_score"] for i in p["items"]]
        assert scores == sorted(scores, reverse=True)


def test_deterministic(pre):
    again = planner.build_all(pre)
    for slug, p in pre.plans.items():
        a = [{k: v for k, v in i.items() if k != "explanation"} for i in p["items"]]
        b = [{k: v for k, v in i.items() if k != "explanation"} for i in again[slug]["items"]]
        assert a == b


def test_methods_exist_and_are_the_most_durable_suitable(pre):
    rc = pre.data.rate_card.set_index("repair_method")
    wo = pre.wo
    for p in pre.plans.values():
        for it in p["items"]:
            m = it["recommended_method"]
            assert m["repair_method"] in rc.index and m["rate_inr"] == rc.loc[m["repair_method"], "standard_rate_inr"]
            # lowest reopen rate among methods used for the same kind of work (with enough history)
            g = wo[wo.work_type == it["_issue"]].groupby("repair_method").reopened.agg(["mean", "size"])
            g = g[g["size"] >= planner.MIN_JOBS_FOR_RATE]
            assert abs(g["mean"].min() * 100 - m["reopen_rate_pct"]) < 0.06, (it["road_id"], it["_issue"])
    # the headline case: for potholes hot mix beats the cheap cold mix on durability
    hot = [i for p in pre.plans.values() for i in p["items"] if i["_issue"] == "Pothole"]
    assert hot and {i["recommended_method"]["repair_method"] for i in hot} == {"Hot mix patch"}
    # where a cheaper suitable method exists it is cold mix; where hot mix is also the cheapest (small typical area) there is none
    assert all(not i["alternatives"] or i["alternatives"][0]["repair_method"] == "Cold mix patch" for i in hot)
    with_alt = [i for i in hot if i["alternatives"]]
    assert len(with_alt) > len(hot) / 2
    assert all(i["alternatives"][0]["reopen_rate_pct"] > i["recommended_method"]["reopen_rate_pct"] for i in with_alt)


def test_cost_comes_from_the_rate_card(pre):
    for p in pre.plans.values():
        for it in p["items"]:
            m = it["recommended_method"]
            if it["_warranty"]:  # the original contractor owes it: ₹0 to the city, standard cost stated in words
                assert it["estimated_cost_inr"] == 0 and it["cost_basis"].startswith("₹0 to the city")
                continue
            if m["unit"] == "per job":
                assert it["area_sqm_estimate"] is None and it["estimated_cost_inr"] == m["rate_inr"]
            else:
                assert abs(it["estimated_cost_inr"] - m["rate_inr"] * it["area_sqm_estimate"]) <= m["rate_inr"] * 0.06  # area rounded to 0.1


def test_budget_fit_is_greedy_and_overspent_wards_fund_only_warranty_repairs(pre):
    over = 0
    for p in pre.plans.values():
        left = max(p["remaining_inr"], 0.0)
        assert abs(p["remaining_inr"] - (p["budget_inr"] - p["spent_inr"])) < 0.01
        for it in p["items"]:
            fits = it["estimated_cost_inr"] <= left
            assert it["within_budget"] == fits, (p["ward_slug"], it["rank"])
            if fits:
                left -= it["estimated_cost_inr"]
        funded = sum(i["estimated_cost_inr"] for i in p["items"] if i["within_budget"])
        assert funded <= max(p["remaining_inr"], 0.0) + 0.01
        if p["remaining_inr"] < 0:
            over += 1
            assert all(i["_warranty"] for i in p["items"] if i["within_budget"])
    assert over >= 5  # the dataset has overspent wards (A, E, R/S, R/C, L, M/W)


def test_complaints_land_on_roads_in_their_own_ward(pre):
    c = pre.data.complaints.set_index("complaint_id")
    roads = pre.data.roads.set_index("road_id")
    checked = 0
    for p in pre.plans.values():
        for it in p["items"]:
            assert roads.loc[it["road_id"], "ward_code"] == p["ward_code"]
            for cid in it["evidence"]["complaint_ids"]:
                assert c.loc[cid, "status"] in planner.OPEN_STATUS
                if isinstance(c.loc[cid, "ward_code"], str):
                    assert c.loc[cid, "ward_code"] == p["ward_code"]
                    checked += 1
    assert checked > 100


def test_evidence_ids_exist_and_chips_match(pre):
    d = pre.data
    acc, hot, fac = set(d.accidents.accident_id), set(d.hotspots.hotspot_id), set(d.facilities.facility_id)
    for p in pre.plans.values():
        for it in p["items"]:
            ev = it["evidence"]
            assert set(ev["accident_ids"]) <= acc and set(ev["hotspot_ids"]) <= hot and set(ev["facility_ids"]) <= fac
            kinds = {r["kind"] for r in it["reasons"]}
            assert ("open_complaints" in kinds) == bool(ev["complaint_ids"])
            assert ("accidents" in kinds) == bool(ev["accident_ids"])
            assert (("ambulance_route" in kinds) or ("school_route" in kinds)) == bool(ev["facility_ids"])


def test_a_hospital_entry_road_gets_facility_points(pre):
    hosp_roads = set(pre.data.facilities[pre.data.facilities.type == "Hospital"].ambulance_entry_road.dropna())
    hits = [i for p in pre.plans.values() for i in p["items"] if i["road_id"] in hosp_roads]
    assert hits
    for it in hits:
        assert next(x for x in it["score_parts"] if x["key"] == "facilities")["points"] >= 14.9
        assert any(r["kind"] == "ambulance_route" for r in it["reasons"])


def test_api_slug_forms_and_city(client):
    assert client.get("/api/plan", params={"ward": "G/S"}).json()["ward_slug"] == "g-s"
    assert client.get("/api/plan", params={"ward": "zz"}).status_code == 404
    city = client.get("/api/plan/city?limit=8").json()
    CityPlanResponse.model_validate(city)
    scores = [r["item"]["risk_score"] for r in city["items"]]
    assert len(scores) == 8 and scores == sorted(scores, reverse=True)
    assert all("_issue" not in r["item"] for r in city["items"])


def test_warranty_repairs_cost_the_city_nothing(pre):
    roads = pre.data.roads.set_index("road_id")
    w = [i for p in pre.plans.values() for i in p["items"] if i["_warranty"]]
    assert w, "the dataset has DLP roads with open surface defects"
    for it in w:
        assert roads.loc[it["road_id"], "under_dlp"] == "Y" and it["_issue"] in planner.DLP_AUDIT_WORK_TYPES
        assert it["estimated_cost_inr"] == 0 and it["within_budget"]
