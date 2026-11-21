"""Evidence pack for one flag. Pydantic is the source of truth; the TS mirror follows in the frontend.

Everything here is deterministic. `claude_review` is a separate opinion and never changes rule or tier.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Verdict = Literal["worth_checking", "likely_justified", "needs_more_info"]


class ClaudeReview(BaseModel):
    verdict: Verdict
    headline: str
    reasoning: str
    context_considered: list[str]
    evidence_refs: list[str]
    explanation: str  # = reasoning (kept for the existing Flag.review shape)
    source: Literal["claude", "template"]
    model: str | None = None


class WorkOrderDetail(BaseModel):
    work_order_id: str
    ward_code: str
    road_id: str
    work_type: str
    repair_method: str
    contractor_id: str
    contractor_name: str
    assigned_at: str
    work_started_at: str | None
    completed_at: str | None
    area_sqm: float | None
    cost_inr: float
    sla_hours: float
    actual_hours: float | None
    sla_ratio: float | None
    sla_met: str
    reopened_within_30d: bool
    engineer_remark: str
    linked_complaint_ids: list[str]


class RateCheck(BaseModel):
    work_order_id: str
    repair_method: str
    unit: str
    standard_rate_inr: float
    area_sqm: float | None
    expected_inr: float
    billed_inr: float
    ratio: float
    normal_range_pct: list[int]
    threshold_x: float
    steps: list[str]


class RoadInfo(BaseModel):
    road_id: str
    road_name: str
    segment_no: int
    road_type: str
    surface: str
    last_resurfaced: str | None
    under_dlp: str
    bus_route: str
    congestion_index_0_10: float | None
    bus_routes_count: int | None
    peak_hour_vehicles: int | None


class ComplaintDetail(BaseModel):
    complaint_id: str
    work_order_id: str  # the flagged work order it is linked to
    received_at: str
    text: str
    language: str
    channel: str
    photo_description: str
    upvotes: int
    status: str


class RainDay(BaseModel):
    date: str
    santacruz_mm: float | None
    colaba_mm: float | None
    imd_alert: str | None


class RainContext(BaseModel):
    window: list[RainDay]
    week_before_mm: dict[str, float]  # per station, 7 days before completion
    week_after_mm: dict[str, float]  # per station, completion day + 6
    max_imd_alert: str | None
    covered_until: str
    note: str | None


class TideDay(BaseModel):
    date: str
    height_m: float


class HotspotNear(BaseModel):
    hotspot_id: str
    name: str
    distance_m: int
    same_ward: bool
    flood_threshold_mm_per_day: float
    tide_sensitive: str
    years_flagged_last_5: int


class Warranty(BaseModel):
    under_dlp: str
    last_resurfaced: str | None
    utility_trench_in_remark: bool
    explanation: str


class ComplaintContext(BaseModel):
    count: int
    total_upvotes: int


class Context(BaseModel):
    rain: RainContext | None
    big_tides: list[TideDay]
    low_lying_index: float
    flood_hotspots: list[HotspotNear]
    warranty: Warranty
    engineer_remark: str
    complaints: ComplaintContext


class RelatedWO(BaseModel):
    work_order_id: str
    relation: str
    repair_method: str
    contractor_id: str
    completed_at: str | None
    cost_inr: float
    reopened_within_30d: bool


class ContractorSummary(BaseModel):
    contractor_id: str
    contractor_name: str
    work_orders: int
    reopen_observed_pct: float
    reopen_expected_pct: float
    reopen_ci_low_pct: float
    reopen_ci_high_pct: float
    sla_met_pct: float
    median_cost_vs_rate: float
    small_sample: bool


class FlagEvidence(BaseModel):
    flag_id: str
    rule: str
    tier: str
    severity: str
    claim: str
    how_we_checked: list[str]
    work_order_ids: list[str]
    work_orders: list[WorkOrderDetail]
    rate_check: RateCheck | None
    rate_checks: list[RateCheck]
    road: RoadInfo
    complaints: list[ComplaintDetail]
    complaints_note: str | None
    context: Context
    related_work_orders: list[RelatedWO]
    contractor: ContractorSummary
    data_notes: list[str]
    claude_review: ClaudeReview | None = None
