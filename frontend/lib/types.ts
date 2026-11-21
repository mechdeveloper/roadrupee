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
