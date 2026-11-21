"use client";

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

function Stat({ href, label, value }: { href: string; label: string; value: string }) {
  return (
    <Link href={href} className="block rounded-xl border bg-surface/90 px-4 py-2.5 transition-shadow hover:shadow-md">
      <span className="block text-[13px] text-muted-foreground">{label}</span>
      <span className="block text-2xl leading-tight font-semibold tracking-tight text-ink">{value}</span>
    </Link>
  );
}

/** Compact hook: the headline number, a small ₹100 bar, three clickable stats, and the Trace box. */
export function HookBand({ summary, error, retry }: { summary: Summary | null; error?: string; retry: () => void }) {
  const t = useT();
  return (
    <header className="hero-sky">
      <TopNav />
      <div className="mx-auto grid w-full max-w-[1280px] gap-6 px-4 pt-2 pb-7 sm:px-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-10">
        <div>
          <p className="text-[13px] font-semibold tracking-[0.14em] text-primary">{t("hero.eyebrow")}</p>
          {summary ? (
            <>
              <h1 className="mt-2 text-4xl leading-[1.05] font-semibold tracking-tight text-ink sm:text-5xl">
                <CountUp value={summary.failed_spend_inr} className="text-scale-1" />{" "}
                <span className="block text-xl leading-snug font-medium sm:text-2xl">
                  {t("hero.rest", { total: inr(summary.total_spend_inr) })}
                </span>
              </h1>
              <div className="mt-4 max-w-[440px]">
                <RupeeBar failedPct={summary.failed_pct} />
              </div>
              <div className="mt-4 grid max-w-xl grid-cols-1 gap-2 sm:grid-cols-3">
                <Stat href="/audit?rule=DLP_PAID" label={t("hook.warranty")} value={inr(summary.dlp_paid_liable_inr)} />
                <Stat href="/audit?rule=OVER_RATE" label={t("hook.rate")} value={inr(summary.over_rate_excess_inr)} />
                <Stat href="/plan" label={t("hook.fatal")} value={num(summary.road_defect_fatal)} />
              </div>
            </>
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
        <div className="self-center">
          <TraceBox />
        </div>
      </div>
    </header>
  );
}
