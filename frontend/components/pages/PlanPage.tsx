"use client";

import Link from "next/link";
import { useMemo } from "react";
import { Chip } from "@/components/Chip";
import { ErrorBox } from "@/components/ErrorBox";
import { PageShell } from "@/components/PageShell";
import { NextRupeeTop5 } from "@/components/home/NextRupeeTop5";
import { Section } from "@/components/home/Section";
import { Skeleton } from "@/components/ui/skeleton";
import { type Ward, useApi } from "@/lib/api";
import { inr } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { wardHref } from "@/lib/wards";

/** /plan: the city's riskiest roads, then a way into each ward's own plan. */
export function PlanPage() {
  const t = useT();
  const { state, retry } = useApi<Ward[]>("/api/wards");
  const wards = useMemo(
    () => (state.status === "ready" ? [...state.data].sort((a, b) => a.ward_code.localeCompare(b.ward_code)) : []),
    [state],
  );
  return (
    <PageShell title={t("home.q.next")} subtitle={t("plan.intro")}>
      <div className="space-y-12">
        <Section id="top" title={t("plan.page.top")}>
          <NextRupeeTop5 limit={10} />
        </Section>
        <Section id="pick" title={t("plan.page.pick")}>
          {state.status === "error" ? (
            <ErrorBox message={state.message} onRetry={retry} />
          ) : state.status === "loading" ? (
            <Skeleton className="h-64 w-full rounded-2xl" aria-busy="true" />
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {wards.map((w) => {
                const left = w.budget_inr - w.spend_inr;
                return (
                  <li key={w.ward_code}>
                    <Link
                      href={wardHref(w.slug, { tab: "next" })}
                      className="flex min-h-[88px] flex-col justify-between rounded-2xl border bg-surface p-3.5 shadow-sm transition-shadow hover:shadow-md"
                    >
                      <span>
                        <span className="text-lg font-semibold text-ink">{w.ward_code}</span>{" "}
                        <span className="text-[13px] text-muted-foreground">{w.ward_name.split(",")[0]}</span>
                      </span>
                      <span className="mt-2">
                        <Chip tone={left < 0 ? "check" : "held"}>
                          {left < 0 ? t("plan.overspentShort") : t("plan.remainingShort", { amount: inr(left) })}
                        </Chip>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Section>
      </div>
    </PageShell>
  );
}
