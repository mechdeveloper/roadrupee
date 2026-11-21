"use client";

import { CircleCheck, Equal, TriangleAlert } from "lucide-react";
import { Chip } from "@/components/Chip";
import type { Ward } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { VERDICT_KEY, VERDICT_SHORT_KEY, verdict } from "@/lib/plain";

/** better (teal) / about as expected (grey) / worse (red): compared with what we'd expect for the ward's rain and flooding. */
export function VerdictChip({
  ward,
  compact = false,
  className,
}: {
  ward: Parameters<typeof verdict>[0] & Partial<Ward>;
  compact?: boolean;
  className?: string;
}) {
  const t = useT();
  const v = verdict(ward);
  const tone = v === "better" ? "held" : v === "worse" ? "check" : "neutral";
  const Icon = v === "better" ? CircleCheck : v === "worse" ? TriangleAlert : Equal;
  return (
    <Chip tone={tone} icon={Icon} className={className}>
      {t((compact ? VERDICT_SHORT_KEY : VERDICT_KEY)[v])}
    </Chip>
  );
}
