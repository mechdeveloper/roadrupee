"use client";

import { ArrowRight, Clock, Copy, Receipt, RotateCcw, ShieldAlert, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { Chip } from "@/components/Chip";
import { ClaudeVerdictChip } from "@/components/ClaudeVerdictChip";
import type { Flag } from "@/lib/api";
import { inr } from "@/lib/format";
import { type Key, useT } from "@/lib/i18n";

const ICON: Record<string, LucideIcon> = {
  OVER_RATE: Receipt,
  DOUBLE_BILL: Copy,
  DLP_PAID: ShieldAlert,
  SLA_BREACH: Clock,
  REPEAT_FAILURE: RotateCcw,
};

export function FlagCard({ flag }: { flag: Flag }) {
  const t = useT();
  const Icon = ICON[flag.rule] ?? Receipt;
  return (
    <Link
      href={`/flag/${flag.flag_id}`}
      className="group flex h-full flex-col rounded-2xl border bg-surface p-4 shadow-sm transition-shadow hover:shadow-md sm:p-5"
    >
      <span className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[var(--tone-check-bg)] text-[var(--tone-check-ink)]">
          <Icon className="size-5" aria-hidden />
        </span>
        <span className="text-[17px] leading-snug font-semibold text-ink">{t(`rule.${flag.rule}.title` as Key)}</span>
      </span>

      {flag.amount_inr > 0 && (
        <span className="mt-3 block">
          <span className="block text-3xl leading-none font-semibold tracking-tight text-ink">{inr(flag.amount_inr)}</span>
          <span className="mt-0.5 block text-[13px] text-muted-foreground">
            {t("check.involved")}
          </span>
        </span>
      )}

      <span className="mt-3 line-clamp-3 text-sm text-muted-foreground">{flag.reason}</span>

      <span className="mt-auto flex flex-wrap items-center gap-2 pt-4">
        <Chip tone="neutral">{t("check.evidence", { id: flag.work_order_ids[0] })}</Chip>
        {flag.review?.verdict && <ClaudeVerdictChip verdict={flag.review.verdict} />}
      </span>
      <span className="mt-3 inline-flex min-h-11 items-center gap-1.5 font-semibold text-primary">
        {t("check.see")}
        <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
      </span>
    </Link>
  );
}
