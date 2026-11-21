"""Contract for POST /api/trace  (Trace my complaint). TypeScript mirror: frontend/lib/types.ts.

Everything factual in the response is deterministic (matching, trail, numbers). Claude only (a) extracts
language / locality / issue type from messy text and (b) writes the answer in the user's language, from the
trail only (numbers guardrail). The RTI draft is a deterministic EN + MR template.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Outcome = Literal[
    "fixed_held", "fixed_failed", "in_progress", "open", "forwarded", "rejected", "not_found", "needs_confirmation"
]
StepStatus = Literal["done", "failed", "pending", "skipped"]


class TraceRequest(BaseModel):
    text: str | None = Field(default=None, description="Free text in Marathi, Hindi, Hinglish or English, or an id")
    complaint_id: str | None = Field(default=None, description="e.g. BMC25-000123")


class TraceComplaint(BaseModel):
    complaint_id: str
    received_at: str
    channel: str
    language: str
    text: str
    locality_text: str
    ward_code: str | None
    category_reported: str
    status: str
    upvotes: int
    photo_description: str
    resolved_at: str | None = None
    score: float | None = Field(default=None, description="match score, only on alternatives")


class Geocoded(BaseModel):
    locality: str
    ward_code: str
    ward_slug: str
    ward_name: str
    lat: float
    lon: float
    match: Literal["exact", "alias", "contained", "prefix", "fuzzy"]


class TraceExtraction(BaseModel):
    language: Literal["en", "hi", "mr", "hi-en"]
    locality: str | None = Field(description="locality normalised to its English gazetteer name, if found")
    geocoded: Geocoded | None
    issue_type: str
    summary: str
    source: Literal["id", "text-match", "claude", "rules"]


class TraceWorkOrder(BaseModel):
    work_order_id: str
    work_type: str
    repair_method: str
    contractor_id: str
    contractor_name: str
    assigned_at: str
    completed_at: str | None
    cost_inr: float
    expected_inr: float
    cost_ratio: float
    within_normal_range: bool
    sla_hours: float
    actual_hours: float | None
    sla_met: str
    reopened_within_30d: bool
    road_id: str
    road_name: str
    under_dlp: bool


class TraceFlag(BaseModel):
    flag_id: str
    rule: str
    tier: str
    severity: str
    reason: str
    amount_inr: float


class StepLink(BaseModel):
    label: str
    href: str


class TraceStep(BaseModel):
    key: Literal["complaint", "issue", "work_order", "held", "warranty", "action"]
    title: str = Field(description="Question-style title, e.g. 'Was it fixed?'")
    status: StepStatus
    headline: str
    detail: str
    links: list[StepLink] = []


class TraceMatch(BaseModel):
    confidence: float
    basis: str = Field(description="how the complaint was found: id | text-match | locality+issue+text | none")
    alternatives: list[TraceComplaint] = []


class TraceAnswer(BaseModel):
    text: str
    language: Literal["en", "hi", "mr", "hi-en"]
    source: Literal["claude", "template"]


class TraceRti(BaseModel):
    en: str
    mr: str


class TraceResponse(BaseModel):
    outcome: Outcome
    input_kind: Literal["id", "text"]
    complaint: TraceComplaint | None
    duplicates: list[TraceComplaint] = []
    extraction: TraceExtraction
    match: TraceMatch
    work_order: TraceWorkOrder | None
    flags: list[TraceFlag] = []
    steps: list[TraceStep] = []
    answer: TraceAnswer
    rti: TraceRti | None
    cached: bool = False
