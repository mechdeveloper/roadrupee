/** Plain-language labels. The ONLY place internal rule names appear in the frontend. */
export const RULE_TITLE: Record<string, string> = {
  OVER_RATE: "Billed well above the standard rate",
  DOUBLE_BILL: "Same repair billed twice within a week, no complaint linked",
  DLP_PAID: "City paid for a repair the original contractor should cover",
  SLA_BREACH: "Took more than twice the target time",
  REPEAT_FAILURE: "Same fix by the same contractor failed again",
};

export function ruleTitle(rule: string): string {
  return RULE_TITLE[rule] ?? "Worth checking";
}

export type Verdict = "better" | "about as expected" | "worse";

/** Observed vs expected reopen rate, only called better/worse when the CI excludes the expectation. */
export function verdict(w: {
  reopen_ci_low_pct?: number;
  reopen_ci_high_pct?: number;
  reopen_expected_pct?: number;
}): Verdict {
  if (w.reopen_ci_low_pct == null || w.reopen_ci_high_pct == null || w.reopen_expected_pct == null)
    return "about as expected";
  if (w.reopen_ci_low_pct > w.reopen_expected_pct) return "worse";
  if (w.reopen_ci_high_pct < w.reopen_expected_pct) return "better";
  return "about as expected";
}
