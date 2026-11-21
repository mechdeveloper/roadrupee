import type { Ward } from "@/lib/api";
import type { PlanItem, PlanResponse, ScoreKey } from "@/lib/types";

/**
 * EXAMPLE data for the next-rupee tab. Used ONLY when GET /api/plan returns 501 (engine not built yet),
 * and always shown with an "Example data" banner. Roads here are fictional; never present this as real.
 */
const PARTS: [ScoreKey, string, number][] = [
  ["complaints", "Open complaints", 30],
  ["flood", "Flooding", 25],
  ["traffic", "Traffic", 15],
  ["accidents", "Accidents", 15],
  ["facilities", "Schools and hospitals", 15],
];

function item(rank: number, name: string, pts: number[], method: PlanItem["recommended_method"], cost: number, reasons: PlanItem["reasons"], basis: string, area: number | null): PlanItem {
  return {
    rank,
    road_id: `EXAMPLE-${rank}`,
    road_name: name,
    segment_no: 1,
    road_type: rank === 1 ? "Arterial" : "Main",
    length_m: 250,
    lat: 19.07,
    lon: 72.87,
    risk_score: pts.reduce((a, b) => a + b, 0),
    score_parts: PARTS.map(([key, label, max], i) => ({ key, label, points: pts[i], max_points: max })),
    reasons,
    recommended_method: method,
    alternatives: [],
    area_sqm_estimate: area,
    estimated_cost_inr: cost,
    cost_basis: basis,
    within_budget: false,
    evidence: { complaint_ids: [], accident_ids: [], hotspot_ids: [], facility_ids: [] },
    explanation: null,
  };
}

export function examplePlan(ward: Ward): PlanResponse {
  const hot: PlanItem["recommended_method"] = {
    repair_method: "Hot mix patch", reopen_rate_pct: 22.6, rate_inr: 2600, unit: "per sqm",
    why: "Hot mix patches reopened less often (22.6%) than cold mix (32.2%), so the dearer repair wastes less money.",
  };
  const pump: PlanItem["recommended_method"] = {
    repair_method: "Dewatering pump deployed", reopen_rate_pct: 14.0, rate_inr: 60000, unit: "per job",
    why: "Of the waterlogging fixes, a pump reopened least often (14.0%).",
  };
  const items = [
    item(1, "Example road 1 (illustrative)", [24, 22.5, 11, 9, 15], hot, 124800, [
      { kind: "flood_hotspot", label: "Floods in heavy rain", detail: "Example", count: null },
      { kind: "ambulance_route", label: "Ambulance entry road for a hospital", detail: "Example", count: 1 },
      { kind: "open_complaints", label: "7 complaints still open", detail: "Example", count: 7 },
      { kind: "accidents", label: "2 accidents blamed on potholes", detail: "Example", count: 2 },
    ], "₹2,600 per sqm × 48 sqm", 48),
    item(2, "Example road 2 (illustrative)", [18, 20, 9, 6, 8], pump, 60000, [
      { kind: "flood_hotspot", label: "Chronic waterlogging spot", detail: "Example", count: null },
      { kind: "tide", label: "Worse on big-tide days", detail: "Example", count: null },
      { kind: "open_complaints", label: "4 complaints still open", detail: "Example", count: 4 },
    ], "₹60,000 per job", null),
    item(3, "Example road 3 (illustrative)", [14, 6, 12, 7, 10], hot, 182000, [
      { kind: "traffic", label: "Busy bus route", detail: "Example", count: null },
      { kind: "school_route", label: "Leads to a municipal school", detail: "Example", count: 1 },
      { kind: "open_complaints", label: "3 complaints still open", detail: "Example", count: 3 },
    ], "₹2,600 per sqm × 70 sqm", 70),
    item(4, "Example road 4 (illustrative)", [9, 3, 7, 4, 0], hot, 78000, [
      { kind: "open_complaints", label: "2 complaints still open", detail: "Example", count: 2 },
      { kind: "traffic", label: "Moderate traffic", detail: "Example", count: null },
    ], "₹2,600 per sqm × 30 sqm", 30),
  ];
  const remaining = ward.budget_inr - ward.spend_inr;
  let left = remaining;
  for (const it of items) {
    it.within_budget = it.estimated_cost_inr <= left;
    if (it.within_budget) left -= it.estimated_cost_inr;
  }
  return {
    ward_slug: ward.slug,
    ward_code: ward.ward_code,
    ward_name: ward.ward_name,
    budget_inr: ward.budget_inr,
    spent_inr: ward.spend_inr,
    remaining_inr: remaining,
    formula: {
      weights: PARTS.map(([key, label, weight]) => ({
        key, label, weight,
        description: {
          complaints: "More unresolved complaints, weighted by severity and 'me too' votes, add more points.",
          flood: "Roads near a chronic flood spot score higher; tide-sensitive spots score highest.",
          traffic: "Busier roads and bus routes score higher.",
          accidents: "Pothole, waterlogging and open-chamber accidents on the road add points.",
          facilities: "Roads that are a hospital's ambulance entry or serve a school score higher.",
        }[key],
      })),
      note: "Items are funded in rank order until the remaining budget runs out.",
    },
    items,
  };
}
