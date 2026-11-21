"""Response models for the ward / contractor / search pages. TypeScript mirror: frontend/lib/types.ts."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Outcome = Literal["held", "failed"]
Alert = Literal["Green", "Yellow", "Orange", "Red"]
Band = Literal["better", "as_expected", "worse", "neutral"]


class Locality(BaseModel):
    locality: str
    ward_code: str
    ward_slug: str
    ward_name: str
    aliases: list[str]  # alternate spellings incl. Devanagari


# ---- money flow (ward page, tab "Where did the money go?") ----
class FlowNode(BaseModel):
    id: str
    label: str
    kind: Literal["spend", "contractor", "method", "outcome"]
    value_inr: float
    outcome: Outcome | None = None
    contractor_id: str | None = None


class FlowLink(BaseModel):
    source: int  # index into nodes
    target: int
    value: float  # rupees
    outcome: Outcome | None = None  # set on the method -> outcome links


class FlowContractor(BaseModel):
    contractor_id: str
    contractor_name: str
    spend_inr: float
    held_inr: float
    failed_inr: float
    failed_pct: float
    work_orders: int


class FlowMethod(BaseModel):
    repair_method: str
    spend_inr: float
    held_inr: float
    failed_inr: float
    failed_pct: float
    work_orders: int


class WardFlow(BaseModel):
    ward_code: str
    ward_slug: str
    ward_name: str
    budget_inr: float
    spend_inr: float
    held_inr: float
    failed_inr: float
    nodes: list[FlowNode]
    links: list[FlowLink]
    contractors: list[FlowContractor]  # ranked by spend, for the mobile-first bars
    methods: list[FlowMethod]


# ---- monsoon timeline (tab "Did the fixes hold?") ----
class TimelineDay(BaseModel):
    date: str
    rain_mm: float | None  # null after rain data ends
    alert: Alert | None
    failed: int  # repairs COMPLETED this day that failed within 30 days
    failed_wo_ids: list[str]


class WardTimeline(BaseModel):
    ward_code: str
    ward_slug: str
    start: str
    end: str
    rain_data_ends: str
    red_alert_days: int
    failed_total: int
    days: list[TimelineDay]


# ---- contractor report card ----
class Grade(BaseModel):
    key: Literal["speed", "durability", "cost", "volume"]
    title: str  # plain question-style title
    band: Band
    headline: str  # one big plain value, e.g. "62% on time"
    detail: str  # plain comparison with the benchmark
    value: float
    benchmark: float | None
    scale_min: float
    scale_max: float
    unit: str


class ContractorWard(BaseModel):
    ward_code: str
    ward_slug: str
    ward_name: str
    work_orders: int
    spend_inr: float
    failed_pct: float
    reopen_expected_pct: float
    small_sample: bool


class ContractorCard(BaseModel):
    contractor_id: str
    contractor_name: str
    empanelled_since: str | None
    wards_active: int
    work_orders: int
    spend_inr: float
    failed_spend_inr: float
    over_rate_count: int
    small_sample: bool
    summary: str
    summary_source: Literal["template", "claude"]
    grades: list[Grade]
    wards: list[ContractorWard]
