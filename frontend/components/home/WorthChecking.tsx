"use client";

import { ArrowRight, Clock, Copy, Receipt, RotateCcw, ShieldAlert, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { Chip } from "@/components/Chip";
import { ClaudeVerdictChip } from "@/components/ClaudeVerdictChip";
import { ErrorBox } from "@/components/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api";
import { inr } from "@/lib/format";
import { type Key, useT } from "@/lib/i18n";
import type { HomeFlag, TopFlags } from "@/lib/types";

export const RULE_ICON: Record<string, LucideIcon> = {
  OVER_RATE: Receipt,
  DOUBLE_BILL: Copy,
  DLP_PAID: ShieldAlert,
  SLA_BREACH: Clock,
  REPEAT_FAILURE: RotateCcw,
};

export function FlagMini({ f }: { f: HomeFlag }) {
  const t = useT();
  const Icon = RULE_ICON[f.rule] ?? Receipt;
  return (
    <Link href={`/flag/${f.flag_id}`} className="group flex h-full flex-col rounded-2xl border bg-surface p-4 shadow-sm transition-shadow hover:shadow-md">
      <span className="flex items-start gap-2.5">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-[var(--tone-check-bg)] text-[var(--tone-check-ink)]">
          <Icon className="size-4.5" aria-hidden />
        </span>
        <span className="text-[15px] leading-snug font-semibold text-ink">{t(`rule.${f.rule}.title` as Key)}</span>
      </span>
      <span className="mt-2 block text-2xl leading-none font-semibold tracking-tight text-ink">{inr(f.amount_inr)}</span>
      <span className="mt-1 block text-[13px] text-muted-foreground">
        {t("picker.ward", { code: f.ward_code })} · {f.ward_name.split(",")[0]}
      </span>
      <span className="mt-2 flex flex-wrap items-center gap-1.5">
        <ClaudeVerdictChip verdict={f.verdict} />
        <Chip tone="neutral">{f.work_order_ids[0]}</Chip>
      </span>
      <span className="mt-auto inline-flex min-h-9 items-center gap-1 pt-2 text-sm font-semibold text-primary">
        {t("check.see")}
        <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden />
      </span>
    </Link>
  );
}

export function WorthChecking() {
  const { state, retry } = useApi<TopFlags>("/api/home/top-flags?limit=6");
  if (state.status === "error") return <ErrorBox message={state.message} onRetry={retry} />;
  if (state.status === "loading")
    return (
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-44 rounded-2xl" />
        ))}
      </div>
    );
  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {state.data.items.map((f) => (
        <li key={f.flag_id}>
          <FlagMini f={f} />
        </li>
      ))}
    </ul>
  );
}
