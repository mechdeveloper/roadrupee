"""Contract tests: the planner example in CLAUDE.md must match the Pydantic model."""
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.contracts.plan import EXAMPLE_PLAN, PlanResponse

CLAUDE_MD = Path(__file__).resolve().parents[2] / "CLAUDE.md"


def _doc_example() -> dict:
    text = CLAUDE_MD.read_text()
    section = text.split("## Planner contract", 1)[1].split("\n## ", 1)[0]
    block = re.search(r"```json\n(.*?)\n```", section, re.S)
    assert block, "CLAUDE.md > Planner contract must contain a ```json example"
    return json.loads(block.group(1))


def test_example_validates_against_model():
    PlanResponse.model_validate(EXAMPLE_PLAN)


def test_claude_md_example_matches_model_example():
    assert _doc_example() == EXAMPLE_PLAN, "CLAUDE.md example drifted from backend/app/contracts/plan.py"


def test_example_follows_the_contract_rules():
    plan = PlanResponse.model_validate(EXAMPLE_PLAN)
    assert sum(w.weight for w in plan.formula.weights) == 100
    assert plan.remaining_inr == plan.budget_inr - plan.spent_inr
    assert [i.rank for i in plan.items] == sorted(i.rank for i in plan.items)
    for item in plan.items:
        # transparent score: parts add up to the headline risk
        assert abs(sum(p.points for p in item.score_parts) - item.risk_score) < 0.01
        assert all(p.points <= p.max_points for p in item.score_parts)


def test_plan_route_returns_contract_for_every_ward():
    from app.main import app

    with TestClient(app) as client:
        wards = client.get("/api/wards").json()
        for w in wards:
            r = client.get("/api/plan", params={"ward": w["slug"]})
            assert r.status_code == 200, w["slug"]
            plan = PlanResponse.model_validate(r.json())
            assert sum(x.weight for x in plan.formula.weights) == 100
            assert plan.remaining_inr == plan.budget_inr - plan.spent_inr
            assert [i.rank for i in plan.items] == list(range(1, len(plan.items) + 1))
            for item in plan.items:
                assert abs(sum(p.points for p in item.score_parts) - item.risk_score) < 0.01
                assert all(p.points <= p.max_points for p in item.score_parts)
        assert client.get("/api/plan", params={"ward": "zz"}).status_code == 404
        schema = client.get("/openapi.json").json()
        assert "PlanResponse" in schema["components"]["schemas"]
