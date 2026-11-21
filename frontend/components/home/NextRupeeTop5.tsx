"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { Chip } from "@/components/Chip";
import { ErrorBox } from "@/components/ErrorBox";
import { Gauge } from "@/components/Gauge";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api";
import { inr } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { CityPlanItem, CityPlanResponse } from "@/lib/types";
import { wardHref } from "@/lib/wards";

function Row({ r, n }: { r: CityPlanItem; n: number }) {
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
              {n}
            </span>
            <span>
              <span className="block font-semibold text-ink">{it.road_name}, segment {it.segment_no}</span>
              <span className="block text-[13px] text-muted-foreground">
                {t("picker.ward", { code: r.ward_code })} · #{it.rank} {t("plan.inWard")} · {it.recommended_method.repair_method}
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
            <Chip key={x.label} tone="neutral" wrap>
              {x.label}
            </Chip>
          ))}
          <ArrowRight className="ml-auto size-4 text-primary transition-transform group-hover:translate-x-0.5" aria-hidden />
        </span>
      </Link>
    </li>
  );
}

/** The riskiest road segments across the city, from the engine (/api/plan/city). */
export function NextRupeeTop5({ limit = 5 }: { limit?: number }) {
  const { state, retry } = useApi<CityPlanResponse>(`/api/plan/city?limit=${limit}`);
  if (state.status === "loading") return <Skeleton className="h-[330px] w-full rounded-2xl" aria-busy="true" />;
  if (state.status === "error") return <ErrorBox message={state.message} onRetry={retry} />;
  return (
    <div className="rounded-2xl border bg-surface p-3 sm:p-4">
      <ol>
        {state.data.items.map((r, i) => (
          <Row key={`${r.ward_slug}-${r.item.road_id}`} r={r} n={i + 1} />
        ))}
      </ol>
    </div>
  );
}
