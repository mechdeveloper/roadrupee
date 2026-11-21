"use client";

import { Sparkles } from "lucide-react";
import { Chip } from "@/components/Chip";
import { type Key, useT } from "@/lib/i18n";
import type { ReviewVerdict } from "@/lib/types";

const KEY: Record<ReviewVerdict, Key> = {
  worth_checking: "claude.worth",
  likely_justified: "claude.justified",
  needs_more_info: "claude.more",
};

/** Claude's view of a flag. Worth checking = red; likely justified / needs more info = grey (context). Renders nothing without a verdict. */
export function ClaudeVerdictChip({ verdict }: { verdict: ReviewVerdict | null | undefined }) {
  const t = useT();
  if (!verdict) return null;
  return (
    <Chip tone={verdict === "worth_checking" ? "check" : "neutral"} icon={Sparkles}>
      {t(KEY[verdict])}
    </Chip>
  );
}
