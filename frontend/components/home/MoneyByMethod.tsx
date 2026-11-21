"use client";

import Link from "next/link";
import { ErrorBox } from "@/components/ErrorBox";
import { SplitBar } from "@/components/ward/SplitBar";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api";
import { inr, pct } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { MethodRow } from "@/lib/types";

/** Spend by repair method, held vs didn't hold. Each row opens the flagged jobs for that repair type. */
export function MoneyByMethod() {
  const t = useT();
  const { state, retry } = useApi<MethodRow[]>("/api/home/methods");
  if (state.status === "error") return <ErrorBox message={state.message} onRetry={retry} />;
  if (state.status === "loading") return <Skeleton className="h-72 w-full rounded-2xl" aria-busy="true" />;
  const max = Math.max(...state.data.map((m) => m.spend_inr), 1);
  return (
    <div className="rounded-2xl border bg-surface p-4 sm:p-5">
      <ul className="grid gap-x-8 gap-y-1 md:grid-cols-2">
        {state.data.map((m) => (
          <li key={m.repair_method}>
            <Link href={`/audit?method=${encodeURIComponent(m.repair_method)}`} className="block rounded-lg px-2 py-2 hover:bg-background">
              <span className="flex items-baseline justify-between gap-3">
                <span className="font-medium text-ink">{m.repair_method}</span>
                <span className="shrink-0 font-semibold text-ink">{inr(m.spend_inr)}</span>
              </span>
              <span className="mt-1 block">
                <SplitBar
                  spend={m.spend_inr}
                  held={m.held_inr}
                  failed={m.failed_inr}
                  max={max}
                  label={`${m.repair_method}: ${t("money.heldAmt", { amount: inr(m.held_inr) })}, ${t("money.failedAmt", { amount: inr(m.failed_inr), pct: pct(m.failed_pct) })}`}
                />
              </span>
              <span className="mt-1 block text-[13px] text-muted-foreground">
                <span className="font-medium text-scale-1">{t("money.failedAmt", { amount: inr(m.failed_inr), pct: pct(m.failed_pct, 0) })}</span> ·{" "}
                {t("money.jobs", { n: m.work_orders })}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <p className="mt-2 px-2 text-[13px] text-muted-foreground">{t("money.rowHint")}</p>
    </div>
  );
}
