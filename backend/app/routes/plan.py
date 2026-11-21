"""GET /api/plan?ward={slug} and /api/plan/city: the next-rupee engine (engine/planner.py), precomputed at startup."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

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
