"""GET /api/plan?ward={slug} and /api/plan/city: the next-rupee engine (engine/planner.py), precomputed at startup."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from ..contracts.plan import CityPlanResponse, PlanResponse
from ..engine import planner

router = APIRouter(prefix="/api")


@router.get("/plan", response_model=PlanResponse)
def plan(request: Request, ward: str = Query(..., description="Ward slug, e.g. 'g-s' for G/S (the code 'G/S' also works)")) -> dict:
    slug = ward.lower().replace("/", "-")
    p = request.app.state.pre.plans.get(slug)
    if p is None:
        raise HTTPException(404, f"Unknown ward '{ward}'")
    return {**p, "items": [planner.public(i) for i in p["items"]]}


@router.get("/plan/city", response_model=CityPlanResponse)
def plan_city(request: Request, limit: int = Query(5, ge=1, le=50)) -> dict:
    """The riskiest road segments across all wards, risk descending."""
    return {"items": planner.city_top(request.app.state.pre.plans, limit)}


PLAN_CSV_PARTS = ("complaints", "flood", "traffic", "accidents", "facilities")


@router.get("/plan.csv")
def plan_csv(request: Request) -> Response:
    """The full next-rupee ranking, one row per ward x ranked item."""
    buf = io.StringIO()
    cols = ["ward_code", "rank", "road_id", "road_name", "segment_no", "risk_score",
            *[f"{k}_points" for k in PLAN_CSV_PARTS], "recommended_method", "estimated_cost_inr", "within_budget"]
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for p in sorted(request.app.state.pre.plans.values(), key=lambda p: p["ward_code"]):
        for i in p["items"]:
            parts = {sp["key"]: sp["points"] for sp in i["score_parts"]}
            w.writerow({
                "ward_code": p["ward_code"], "rank": i["rank"], "road_id": i["road_id"], "road_name": i["road_name"],
                "segment_no": i["segment_no"], "risk_score": i["risk_score"],
                **{f"{k}_points": parts.get(k, "") for k in PLAN_CSV_PARTS},
                "recommended_method": i["recommended_method"]["repair_method"],
                "estimated_cost_inr": i["estimated_cost_inr"], "within_budget": i["within_budget"],
            })
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="roadrupee_plan.csv"'})
