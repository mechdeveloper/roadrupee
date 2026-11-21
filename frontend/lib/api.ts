"use client";

import { useCallback, useEffect, useState } from "react";

export type Summary = {
  total_spend_inr: number;
  failed_spend_inr: number;
  failed_pct: number;
  work_orders: number;
  failed_work_orders: number;
  dlp_paid_total_inr: number;
  dlp_paid_total_count: number;
  dlp_paid_liable_inr: number;
  dlp_paid_liable_count: number;
  over_rate_excess_inr: number;
  over_rate_count: number;
  road_defect_fatal: number;
  road_defect_grievous: number;
  road_defect_accidents: number;
  flag_counts: Record<string, { count: number; audit: number; review: number; amount_inr: number }>;
};

export type AiSummary = { en: string; hi: string; mr: string };

export type Ward = {
  ward_code: string;
  slug: string; // G/S -> g-s, used in /ward/[slug]
  localities: string[];
  /** Claude's plain-language summary of the ward, precomputed by another session. Hide the card when absent. */
  ai_summary?: AiSummary | null;
  ward_name: string;
  budget_inr: number;
  remaining_budget_inr: number;
  spend_inr: number;
  failed_spend_inr: number;
  failed_pct: number;
  work_orders: number;
  low_lying_index: number;
  flags_audit: number;
  flags_review: number;
  reopen_observed_pct: number;
  reopen_expected_pct: number;
  reopen_ci_low_pct: number;
  reopen_ci_high_pct: number;
};

export type Flag = {
  flag_id: string;
  rule: string;
  tier: "audit" | "review";
  severity: "high" | "medium" | "low";
  work_order_ids: string[];
  reason: string;
  ward_code: string;
  road_id: string;
  cost_inr: number;
  amount_inr: number;
  /** Claude's review of the flag (verdict, headline, reasoning, source). Render only if present. */
  review?: Partial<import("@/lib/types").ClaudeReview> | null;
  /** rule-specific evidence; SILENT_FAILURE carries the social posts */
  extra?: { posts?: import("@/lib/types").SocialPost[] } | null;
};

export type State<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

/** Browser only ever calls same-origin /api/*. */
export function useApi<T>(path: string): { state: State<T>; retry: () => void } {
  const [state, setState] = useState<State<T>>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    fetch(path)
      .then(async (r) => {
        if (!r.ok) throw new Error(`Request failed (${r.status})`);
        return (await r.json()) as T;
      })
      .then((data) => live && setState({ status: "ready", data }))
      .catch((e: Error) => live && setState({ status: "error", message: e.message }));
    return () => {
      live = false;
    };
  }, [path, attempt]);

  const retry = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((a) => a + 1);
  }, []);
  return { state, retry };
}
