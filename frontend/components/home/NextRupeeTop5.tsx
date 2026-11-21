"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { Chip } from "@/components/Chip";
import { ErrorBox } from "@/components/ErrorBox";
import { Gauge } from "@/components/Gauge";
import { Skeleton } from "@/components/ui/skeleton";
import { type Ward, useApi } from "@/lib/api";
import { inr } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { examplePlan } from "@/lib/placeholder/plan";
import type { CityPlanItem, CityPlanResponse } from "@/lib/types";
import { wardHref } from "@/lib/wards";

function Row({ r, example }: { r: CityPlanItem; example?: boolean }) {
  const t = useT();
  const it = r.item;
  return (
    <li>
      <Link
        href={wardHref(r.ward_slug, { tab: "next" })}
        className="group block rounded-xl p-3 hover:bg-background"
      >
        <span className="flex items-start justify-between gap-3">
          <span className="flex items-start gap-2.5">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-semibold text-primary">
              {example ? it.rank : it.rank}
            </span>
            <span>
              <span className="block font-semibold text-ink">{it.road_name}</span>
              <span className="block text-[13px] text-muted-foreground">
                {t("picker.ward", { code: r.ward_code })} · {it.recommended_method.repair_method}
              </span>
            </span>
          </span>
          <span className="shrink-0 text-right">
            <span className="block text-xl leading-none font-semibold text-ink">{Math.round(it.risk_score)}</span>
            <span className="text-[12px] text-muted-foreground">{inr(it.estimated_cost_inr)}</span>
          </span>
        </span>
        <span className="mt-2 block">
          <Gauge value={it.risk_score} min={0} max={100} band={it.risk_score >= 60 ? "worse" : "neutral"} label={t("plan.risk", { score: Math.round(it.risk_score) })} />
        </span>
        <span className="mt-2 flex flex-wrap items-center gap-1.5">
          {it.reasons.slice(0, 2).map((x) => (
            <Chip key={x.label} tone="neutral">
              {x.label}
            </Chip>
          ))}
          <ArrowRight className="ml-auto size-4 text-primary transition-transform group-hover:translate-x-0.5" aria-hidden />
        </span>
      </Link>
    </li>
  );
}

/** Top riskiest roads across the city. Labelled example data only while /api/plan/city returns 501. */
export function NextRupeeTop5({ wards }: { wards: Ward[] }) {
  const t = useT();
  const { state, retry } = useApi<CityPlanResponse>("/api/plan/city?limit=5");
  const example = state.status === "error" && state.message.includes("501");

  if (state.status === "loading") return <Skeleton className="h-[330px] w-full rounded-2xl" aria-busy="true" />;
  if (state.status === "error" && !example) return <ErrorBox message={state.message} onRetry={retry} />;

  const rows: CityPlanItem[] =
    state.status === "ready"
      ? state.data.items
      : wards[0]
        ? examplePlan(wards[0]).items.map((item) => ({ ward_slug: wards[0].slug, ward_code: wards[0].ward_code, ward_name: wards[0].ward_name, item }))
        : [];

  return (
    <div className="rounded-2xl border bg-surface p-3 sm:p-4">
      {example && (
        <p role="note" className="mb-2 rounded-lg border border-dashed p-2.5 text-[13px] font-medium text-ink">
          {t("plan.example")}
        </p>
      )}
      <ol>
        {rows.slice(0, 5).map((r) => (
          <Row key={`${r.ward_slug}-${r.item.road_id}`} r={r} example={example} />
        ))}
      </ol>
    </div>
  );
}
