"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { ErrorBox } from "@/components/ErrorBox";
import { TopNav } from "@/components/TopNav";
import { CountUp } from "@/components/hero/CountUp";
import { RupeeBar } from "@/components/hero/RupeeBar";
import { TraceBox } from "@/components/home/TraceBox";
import { Skeleton } from "@/components/ui/skeleton";
import type { Summary } from "@/lib/api";
import { inr, num } from "@/lib/format";
import { useT } from "@/lib/i18n";

function Stat({ href, label, value, tone, cta }: { href: string; label: string; value: string; tone: "red" | "amber"; cta: string }) {
  const ink = tone === "red" ? "text-scale-1" : "text-[var(--tone-watch-ink)]";
  return (
    <Link
      href={href}
      className="group grid grid-cols-[7rem_minmax(0,1fr)] items-center gap-x-4 gap-y-0.5 rounded-2xl border bg-surface/90 px-4 py-3 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:shadow-sm"
    >
      <span className={`row-span-2 text-3xl leading-none font-semibold tracking-tight ${ink}`}>{value}</span>
      <span className="block text-[14px] leading-snug text-ink">{label}</span>
      <span className="inline-flex min-h-8 items-center gap-1 text-sm font-semibold text-primary">
        {cta}
        <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden />
      </span>
    </Link>
  );
}

/** Hero: Trace first (the action), then the hook number, the ₹100 bar with its legend, and three clickable stats. */
export function HookBand({ summary, error, retry }: { summary: Summary | null; error?: string; retry: () => void }) {
  const t = useT();
  return (
    <header className="hero-sky">
      <TopNav />
      <div className="mx-auto w-full max-w-[1280px] px-4 pt-2 pb-7 sm:px-6">
        <TraceBox />

        <div className="mt-8">
          <p className="text-[13px] font-semibold tracking-[0.14em] text-primary">{t("hero.eyebrow")}</p>
          {summary ? (
            <div className="mt-2 grid gap-5 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:items-center lg:gap-10">
              <div>
                <h1 className="max-w-4xl text-2xl leading-snug font-medium tracking-tight text-ink sm:text-3xl">
                  <CountUp value={summary.failed_spend_inr} className="text-5xl leading-none font-semibold text-scale-1 sm:text-6xl" />{" "}
                  {t("hero.rest", { total: inr(summary.total_spend_inr) })}
                </h1>
                <div className="mt-4 max-w-[520px]">
                  <RupeeBar failedPct={summary.failed_pct} />
                </div>
              </div>
              <div className="grid grid-cols-1 gap-3">
                <Stat tone="red" href="/audit?rule=DLP_PAID" label={t("hook.warranty")} value={inr(summary.dlp_paid_liable_inr)} cta={t("hook.seeJobs")} />
                <Stat
                  tone="amber"
                  href="/audit?rule=OVER_RATE"
                  label={t("hook.rate", { n: num(summary.over_rate_count) })}
                  value={inr(summary.over_rate_excess_inr)}
                  cta={t("hook.seeJobs")}
                />
                <Stat tone="red" href="/plan" label={t("hook.fatal")} value={num(summary.road_defect_fatal)} cta={t("hook.seeRoads")} />
              </div>
            </div>
          ) : error ? (
            <div className="mt-3 max-w-xl">
              <ErrorBox message={error} onRetry={retry} />
            </div>
          ) : (
            <div className="mt-3" aria-busy="true">
              <Skeleton className="h-12 w-64" />
              <Skeleton className="mt-3 h-6 w-full max-w-md" />
              <Skeleton className="mt-4 h-24 w-full max-w-[440px]" />
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
