"use client";

import { Ambulance, Bus, Car, Droplets, MessageSquareText, School, Sparkles, TriangleAlert, Waves, type LucideIcon } from "lucide-react";
import { Chip } from "@/components/Chip";
import { Gauge } from "@/components/Gauge";
import { inr, pct } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { PlanItem, ReasonKind } from "@/lib/types";

const REASON_ICON: Record<ReasonKind, LucideIcon> = {
  flood_hotspot: Droplets,
  tide: Waves,
  ambulance_route: Ambulance,
  school_route: School,
  accidents: TriangleAlert,
  open_complaints: MessageSquareText,
  traffic: Car,
  bus_route: Bus,
};

export function RoadCard({
  item,
  selected,
  onToggle,
}: {
  item: PlanItem;
  selected: boolean;
  onToggle: () => void;
}) {
  const t = useT();
  const m = item.recommended_method;
  const alt = item.alternatives[0];
  const ev = item.evidence;
  const evidence = [
    ...ev.complaint_ids.map((id) => ["Complaint", id]),
    ...ev.accident_ids.map((id) => ["Accident", id]),
    ...ev.hotspot_ids.map((id) => ["Flood spot", id]),
    ...ev.facility_ids.map((id) => ["Facility", id]),
  ];

  return (
    <article
      className={`flex h-full flex-col rounded-2xl border bg-surface p-4 shadow-sm sm:p-5 ${
        selected ? "border-primary ring-1 ring-primary" : ""
      } ${selected ? "" : "print:hidden"}`}
    >
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent text-base font-semibold text-primary">
          {item.rank}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-xl leading-snug font-semibold tracking-tight text-ink">{item.road_name}</h3>
          <p className="text-[13px] text-muted-foreground">
            Segment {item.segment_no} · {item.road_type} · {Math.round(item.length_m)} m
          </p>
        </div>
        <div className="text-right">
          <p className="text-3xl leading-none font-semibold text-ink">{Math.round(item.risk_score)}</p>
          <p className="text-[12px] text-muted-foreground">{t("plan.risk", { score: Math.round(item.risk_score) })}</p>
        </div>
      </div>

      <div className="mt-3">
        <Gauge
          value={item.risk_score}
          min={0}
          max={100}
          band={item.risk_score >= 60 ? "worse" : "neutral"}
          label={t("plan.risk", { score: Math.round(item.risk_score) })}
        />
      </div>

      <ul className="mt-3 flex flex-wrap gap-2">
        {item.reasons.map((r) => {
          const Icon = REASON_ICON[r.kind];
          return (
            <li key={`${r.kind}-${r.label}`}>
              <Chip tone="neutral" icon={Icon}>
                {r.label}
              </Chip>
            </li>
          );
        })}
      </ul>

      <div className="mt-4 rounded-xl bg-background p-3.5">
        <p className="text-[13px] font-semibold tracking-wide text-muted-foreground uppercase">{t("plan.method")}</p>
        <p className="mt-0.5 text-lg font-semibold text-ink">{m.repair_method}</p>
        <p className="mt-1 text-sm text-ink">{m.why}</p>
        <p className="mt-1 text-[13px] text-muted-foreground">{t("plan.reopen", { pct: pct(m.reopen_rate_pct) })}</p>
        {alt && (
          <p className="mt-1 text-[13px] text-muted-foreground">
            {t("plan.alt", { method: alt.repair_method, cost: inr(alt.estimated_cost_inr), pct: pct(alt.reopen_rate_pct, 0) })}
          </p>
        )}
        <div className="mt-3 flex flex-wrap items-end justify-between gap-2">
          <p>
            <span className="block text-[13px] text-muted-foreground">{t("plan.cost")}</span>
            <span className="text-2xl font-semibold text-ink">{inr(item.estimated_cost_inr)}</span>
            <span className="block text-[13px] text-muted-foreground">{item.cost_basis}</span>
          </p>
          <Chip tone={item.within_budget ? "held" : "neutral"}>{item.within_budget ? t("plan.fits") : t("plan.beyond")}</Chip>
        </div>
      </div>

      {item.explanation && (
        <p className="mt-3 flex gap-2 text-sm text-ink">
          <Sparkles className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
          {item.explanation}
        </p>
      )}

      <details className="mt-3 text-sm print:hidden">
        <summary className="min-h-11 cursor-pointer py-2.5 font-medium text-primary">{t("plan.how")}</summary>
        <ul className="space-y-2 pb-1">
          {item.score_parts.map((p) => (
            <li key={p.key}>
              <div className="flex justify-between text-[13px]">
                <span>{p.label}</span>
                <span className="font-semibold">
                  {p.points} / {p.max_points}
                </span>
              </div>
              <Gauge value={p.points} min={0} max={p.max_points} band="neutral" label={`${p.label}: ${p.points} of ${p.max_points}`} />
            </li>
          ))}
        </ul>
      </details>

      {evidence.length > 0 && (
        <details className="text-sm print:hidden">
          <summary className="min-h-11 cursor-pointer py-2.5 font-medium text-primary">
            {t("plan.evidence")} ({evidence.length})
          </summary>
          <ul className="flex flex-wrap gap-1.5 pb-1">
            {evidence.map(([kind, id]) => (
              <li key={`${kind}-${id}`}>
                <Chip tone="neutral" className="font-mono">
                  {id}
                </Chip>
              </li>
            ))}
          </ul>
        </details>
      )}

      <label className="mt-auto flex min-h-12 cursor-pointer items-center gap-3 pt-3 text-[16px] font-semibold text-ink print:hidden">
        <input type="checkbox" checked={selected} onChange={onToggle} className="size-6 accent-[var(--accent)]" />
        {t("plan.fund")}
      </label>
    </article>
  );
}
