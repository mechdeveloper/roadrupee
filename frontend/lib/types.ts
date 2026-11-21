/** Shared data contracts (mirror of backend/app/contracts/*.py). Change both sides in the same commit. */

// ---------- Planner: GET /api/plan?ward={slug}  (engine: Student C; UI: tech lead) ----------
// See CLAUDE.md > "Planner contract". The route returns 501 until the engine exists.

export type ScoreKey = "complaints" | "flood" | "traffic" | "accidents" | "facilities";
export type ReasonKind =
  | "flood_hotspot"
  | "tide"
  | "ambulance_route"
  | "school_route"
  | "accidents"
  | "open_complaints"
  | "traffic"
  | "bus_route";

export type FormulaWeight = { key: ScoreKey; label: string; weight: number; description: string };
export type Formula = { weights: FormulaWeight[]; note: string };
export type ScorePart = { key: ScoreKey; label: string; points: number; max_points: number };
export type Reason = { kind: ReasonKind; label: string; detail: string; count: number | null };
export type RecommendedMethod = {
  repair_method: string;
  reopen_rate_pct: number;
  rate_inr: number;
  unit: "per sqm" | "per job";
  why: string;
};
export type Alternative = { repair_method: string; reopen_rate_pct: number; estimated_cost_inr: number };
export type PlanEvidence = {
  complaint_ids: string[];
  accident_ids: string[];
  hotspot_ids: string[];
  facility_ids: string[];
};

export type PlanItem = {
  rank: number; // 1 = fix first
  road_id: string;
  road_name: string;
  segment_no: number;
  road_type: string;
  length_m: number;
  lat: number;
  lon: number;
  risk_score: number; // 0-100, equals the sum of score_parts[].points
  score_parts: ScorePart[];
  reasons: Reason[];
  recommended_method: RecommendedMethod; // most durable, not cheapest
  alternatives: Alternative[];
  area_sqm_estimate: number | null; // null for per-job methods
  estimated_cost_inr: number;
  cost_basis: string;
  within_budget: boolean; // greedy fit in rank order against remaining_inr
  evidence: PlanEvidence;
  explanation: string | null; // Claude's one-liner; null until wired
};

export type PlanResponse = {
  ward_slug: string;
  ward_code: string;
  ward_name: string;
  budget_inr: number;
  spent_inr: number;
  remaining_inr: number; // budget - spent, can be <= 0
  formula: Formula;
  items: PlanItem[]; // ranked, rank 1 first
};

// ---------- Ward / contractor / search pages (mirror of backend/app/contracts/pages.py) ----------
export type Outcome = "held" | "failed";
export type Alert = "Green" | "Yellow" | "Orange" | "Red";
export type Band = "better" | "as_expected" | "worse" | "neutral";

export type Locality = {
  locality: string;
  ward_code: string;
  ward_slug: string;
  ward_name: string;
  aliases: string[]; // incl. Devanagari
};

export type FlowNode = {
  id: string;
  label: string;
  kind: "spend" | "contractor" | "method" | "outcome";
  value_inr: number;
  outcome: Outcome | null;
  contractor_id: string | null;
};
export type FlowLink = { source: number; target: number; value: number; outcome: Outcome | null };
export type FlowContractor = {
  contractor_id: string;
  contractor_name: string;
  spend_inr: number;
  held_inr: number;
  failed_inr: number;
  failed_pct: number;
  work_orders: number;
};
export type FlowMethod = {
  repair_method: string;
  spend_inr: number;
  held_inr: number;
  failed_inr: number;
  failed_pct: number;
  work_orders: number;
};
export type WardFlow = {
  ward_code: string;
  ward_slug: string;
  ward_name: string;
  budget_inr: number;
  spend_inr: number;
  held_inr: number;
  failed_inr: number;
  nodes: FlowNode[];
  links: FlowLink[];
  contractors: FlowContractor[];
  methods: FlowMethod[];
};

export type TimelineDay = {
  date: string;
  rain_mm: number | null; // null after rain data ends
  alert: Alert | null;
  failed: number; // repairs COMPLETED this day that failed within 30 days
  failed_wo_ids: string[];
};
export type WardTimeline = {
  ward_code: string;
  ward_slug: string;
  start: string;
  end: string;
  rain_data_ends: string;
  red_alert_days: number;
  failed_total: number;
  days: TimelineDay[];
};

export type Grade = {
  key: "speed" | "durability" | "cost" | "volume";
  title: string;
  band: Band;
  headline: string;
  detail: string;
  value: number;
  benchmark: number | null;
  scale_min: number;
  scale_max: number;
  unit: string;
};
export type ContractorWard = {
  ward_code: string;
  ward_slug: string;
  ward_name: string;
  work_orders: number;
  spend_inr: number;
  failed_pct: number;
  reopen_expected_pct: number;
  small_sample: boolean;
};
export type ContractorCard = {
  contractor_id: string;
  contractor_name: string;
  empanelled_since: string | null;
  wards_active: number;
  work_orders: number;
  spend_inr: number;
  failed_spend_inr: number;
  over_rate_count: number;
  small_sample: boolean;
  summary: string;
  summary_source: "template" | "claude";
  grades: Grade[];
  wards: ContractorWard[];
};

// ---------- Evidence page: GET /api/flags/{id}/evidence (mirror of backend/app/contracts/evidence.py) ----------
export type ReviewVerdict = "worth_checking" | "likely_justified" | "needs_more_info";

export type ClaudeReview = {
  verdict: ReviewVerdict;
  headline: string;
  reasoning: string;
  context_considered: string[];
  evidence_refs: string[];
  explanation: string; // = reasoning
  source: "claude" | "template"; // template = deterministic fallback when Claude is unavailable
  model: string | null;
};

export type WorkOrderDetail = {
  work_order_id: string;
  ward_code: string;
  road_id: string;
  work_type: string;
  repair_method: string;
  contractor_id: string;
  contractor_name: string;
  assigned_at: string;
  work_started_at: string | null;
  completed_at: string | null;
  area_sqm: number | null;
  cost_inr: number;
  sla_hours: number;
  actual_hours: number | null;
  sla_ratio: number | null;
  sla_met: string;
  reopened_within_30d: boolean;
  engineer_remark: string;
  linked_complaint_ids: string[];
};

export type RateCheck = {
  work_order_id: string;
  repair_method: string;
  unit: string;
  standard_rate_inr: number;
  area_sqm: number | null;
  expected_inr: number;
  billed_inr: number;
  ratio: number;
  normal_range_pct: number[];
  threshold_x: number;
  steps: string[];
};

export type RoadInfo = {
  road_id: string;
  road_name: string;
  segment_no: number;
  road_type: string;
  surface: string;
  last_resurfaced: string | null;
  under_dlp: string;
  bus_route: string;
  congestion_index_0_10: number | null;
  bus_routes_count: number | null;
  peak_hour_vehicles: number | null;
};

export type ComplaintDetail = {
  complaint_id: string;
  work_order_id: string;
  received_at: string;
  text: string;
  language: string;
  channel: string;
  photo_description: string;
  upvotes: number;
  status: string;
};

export type RainDay = { date: string; santacruz_mm: number | null; colaba_mm: number | null; imd_alert: string | null };
export type RainContext = {
  window: RainDay[];
  week_before_mm: Record<string, number>;
  week_after_mm: Record<string, number>;
  max_imd_alert: string | null;
  covered_until: string;
  note: string | null;
};
export type HotspotNear = {
  hotspot_id: string;
  name: string;
  distance_m: number;
  same_ward: boolean;
  flood_threshold_mm_per_day: number;
  tide_sensitive: string;
  years_flagged_last_5: number;
};
export type Warranty = {
  under_dlp: string;
  last_resurfaced: string | null;
  utility_trench_in_remark: boolean;
  explanation: string;
};
export type EvidenceContext = {
  rain: RainContext | null;
  big_tides: { date: string; height_m: number }[];
  low_lying_index: number;
  flood_hotspots: HotspotNear[];
  warranty: Warranty;
  engineer_remark: string;
  complaints: { count: number; total_upvotes: number };
};
export type RelatedWO = {
  work_order_id: string;
  relation: string;
  repair_method: string;
  contractor_id: string;
  completed_at: string | null;
  cost_inr: number;
  reopened_within_30d: boolean;
};
export type ContractorSummary = {
  contractor_id: string;
  contractor_name: string;
  work_orders: number;
  reopen_observed_pct: number;
  reopen_expected_pct: number;
  reopen_ci_low_pct: number;
  reopen_ci_high_pct: number;
  sla_met_pct: number;
  median_cost_vs_rate: number;
  small_sample: boolean;
};

export type FlagEvidence = {
  flag_id: string;
  rule: string;
  tier: string;
  severity: string;
  claim: string; // one plain sentence
  how_we_checked: string[];
  work_order_ids: string[];
  work_orders: WorkOrderDetail[];
  rate_check: RateCheck | null;
  rate_checks: RateCheck[];
  road: RoadInfo;
  complaints: ComplaintDetail[];
  complaints_note: string | null;
  context: EvidenceContext;
  related_work_orders: RelatedWO[];
  contractor: ContractorSummary;
  data_notes: string[];
  claude_review: ClaudeReview | null;
};
