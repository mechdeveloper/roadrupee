"""Contract for GET /api/plan?ward={slug}  (next-rupee planner).

Owner of the ENGINE that fills this: Student C. Owner of the UI that renders it: tech lead.
Both sides code against these models; the TypeScript mirror is frontend/lib/types.ts and the
human-readable description is CLAUDE.md > "Planner contract". Until the engine exists the
route returns HTTP 501 and the frontend shows clearly labelled example data.

Rules the engine must follow (judged: "budget smarts"):
  * risk_score is 0-100 and is the SUM of score_parts[].points (transparent, shown in the UI).
  * recommend the most DURABLE method (lowest 30-day reopen rate among methods suited to the
    issue), not the cheapest.
  * rank by risk_score; mark within_budget greedily down the ranking against remaining_inr.
  * every number links to evidence: fill evidence.* ids.
  * all arithmetic is deterministic Python. Claude only writes `explanation`.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ScoreKey = Literal["complaints", "flood", "traffic", "accidents", "facilities"]
ReasonKind = Literal[
    "flood_hotspot", "tide", "ambulance_route", "school_route",
    "accidents", "open_complaints", "traffic", "bus_route",
]


class FormulaWeight(BaseModel):
    key: ScoreKey
    label: str = Field(description="Plain-language name, e.g. 'Open complaints'")
    weight: float = Field(description="Maximum points this part can add. All weights sum to 100.")
    description: str = Field(description="One plain sentence on how the points are earned")


class Formula(BaseModel):
    weights: list[FormulaWeight]
    note: str = Field(description="Shown under the formula, e.g. how ties and budget fit work")


class ScorePart(BaseModel):
    key: ScoreKey
    label: str
    points: float = Field(ge=0)
    max_points: float = Field(gt=0)


class Reason(BaseModel):
    kind: ReasonKind = Field(description="Picks the icon chip in the UI")
    label: str = Field(description="Plain English, e.g. 'Floods when rain passes 80 mm a day'")
    detail: str = Field(description="One more line of context")
    count: int | None = Field(default=None, description="e.g. number of open complaints")


class RecommendedMethod(BaseModel):
    repair_method: str = Field(description="Must be a repair_method in data/rate_card.csv")
    reopen_rate_pct: float = Field(description="Observed 30-day reopen rate for this method, percent")
    rate_inr: float = Field(description="standard_rate_inr from the rate card")
    unit: Literal["per sqm", "per job"]
    why: str = Field(description="Plain reason it is the most durable choice, not the cheapest")


class Alternative(BaseModel):
    repair_method: str
    reopen_rate_pct: float
    estimated_cost_inr: float


class PlanEvidence(BaseModel):
    complaint_ids: list[str] = []
    accident_ids: list[str] = []
    hotspot_ids: list[str] = []
    facility_ids: list[str] = []


class PlanItem(BaseModel):
    rank: int = Field(ge=1, description="1 = fix first")
    road_id: str
    road_name: str
    segment_no: int
    road_type: str
    length_m: float
    lat: float = Field(description="Segment midpoint")
    lon: float
    risk_score: float = Field(ge=0, le=100)
    score_parts: list[ScorePart] = Field(description="points sum to risk_score")
    reasons: list[Reason]
    recommended_method: RecommendedMethod
    alternatives: list[Alternative] = []
    area_sqm_estimate: float | None = Field(default=None, description="null for per-job methods")
    estimated_cost_inr: float
    cost_basis: str = Field(description="How the cost was derived, e.g. '₹2,600 per sqm × 48 sqm'")
    within_budget: bool = Field(description="True if this item still fits remaining_inr when funded in rank order")
    evidence: PlanEvidence
    explanation: str | None = Field(default=None, description="Claude's one-line explanation; null until wired")


class PlanResponse(BaseModel):
    ward_slug: str
    ward_code: str
    ward_name: str
    budget_inr: float
    spent_inr: float
    remaining_inr: float = Field(description="budget_inr - spent_inr. Can be zero or negative.")
    formula: Formula
    items: list[PlanItem] = Field(description="Ranked, rank 1 first. Around 5 to 15 items.")


class CityPlanItem(BaseModel):
    ward_slug: str
    ward_code: str
    ward_name: str
    item: PlanItem


class CityPlanResponse(BaseModel):
    """GET /api/plan/city?limit=N: the riskiest road segments across all wards, risk_score descending."""
    items: list[CityPlanItem]


EXAMPLE_PLAN: dict = {
    "ward_slug": "g-s",
    "ward_code": "G/S",
    "ward_name": "Worli, Lower Parel, Prabhadevi",
    "budget_inr": 1400000,
    "spent_inr": 1020000,
    "remaining_inr": 380000,
    "formula": {
        "weights": [
            {"key": "complaints", "label": "Open complaints", "weight": 30,
             "description": "More unresolved complaints, weighted by severity and 'me too' votes, add more points."},
            {"key": "flood", "label": "Flooding", "weight": 25,
             "description": "Roads near a chronic flood spot score higher; tide-sensitive spots score highest."},
            {"key": "traffic", "label": "Traffic", "weight": 15,
             "description": "Busier roads and bus routes score higher."},
            {"key": "accidents", "label": "Accidents", "weight": 15,
             "description": "Pothole, waterlogging and open-chamber accidents on the road add points."},
            {"key": "facilities", "label": "Schools and hospitals", "weight": 15,
             "description": "Roads that are a hospital's ambulance entry or serve a school score higher."},
        ],
        "note": "Items are funded in rank order until the remaining budget runs out.",
    },
    "items": [
        {
            "rank": 1,
            "road_id": "RD0151",
            "road_name": "Dr E Moses Road",
            "segment_no": 2,
            "road_type": "Arterial",
            "length_m": 310,
            "lat": 18.9985,
            "lon": 72.8292,
            "risk_score": 81.5,
            "score_parts": [
                {"key": "complaints", "label": "Open complaints", "points": 24.0, "max_points": 30},
                {"key": "flood", "label": "Flooding", "points": 22.5, "max_points": 25},
                {"key": "traffic", "label": "Traffic", "points": 11.0, "max_points": 15},
                {"key": "accidents", "label": "Accidents", "points": 9.0, "max_points": 15},
                {"key": "facilities", "label": "Schools and hospitals", "points": 15.0, "max_points": 15},
            ],
            "reasons": [
                {"kind": "flood_hotspot", "label": "Floods when rain passes 75 mm a day",
                 "detail": "Flagged in 4 of the last 5 years", "count": None},
                {"kind": "ambulance_route", "label": "Ambulance entry road for a hospital",
                 "detail": "Serves an emergency department", "count": 1},
                {"kind": "open_complaints", "label": "7 complaints still open",
                 "detail": "Most recent 3 days ago", "count": 7},
                {"kind": "accidents", "label": "2 accidents blamed on potholes",
                 "detail": "1 fatal, 1 grievous", "count": 2},
            ],
            "recommended_method": {
                "repair_method": "Hot mix patch",
                "reopen_rate_pct": 22.6,
                "rate_inr": 2600,
                "unit": "per sqm",
                "why": "Hot mix patches reopened less often (22.6%) than cold mix (32.2%), so the dearer repair wastes less money.",
            },
            "alternatives": [
                {"repair_method": "Cold mix patch", "reopen_rate_pct": 32.2, "estimated_cost_inr": 86400},
            ],
            "area_sqm_estimate": 48,
            "estimated_cost_inr": 124800,
            "cost_basis": "₹2,600 per sqm × 48 sqm",
            "within_budget": True,
            "evidence": {
                "complaint_ids": ["BMC25-001234", "BMC25-001301"],
                "accident_ids": ["ACC-0042", "ACC-0107"],
                "hotspot_ids": ["FH07"],
                "facility_ids": ["FAC-021"],
            },
            "explanation": None,
        }
    ],
}
