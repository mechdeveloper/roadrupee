import { TopNav } from "@/components/TopNav";
import { CountUp } from "@/components/hero/CountUp";
import { HeroTrace } from "@/components/hero/HeroTrace";
import { RainLayer } from "@/components/hero/RainLayer";
import { RupeeBar } from "@/components/hero/RupeeBar";
import { Skeleton } from "@/components/ui/skeleton";
import type { Summary } from "@/lib/api";
import { inr } from "@/lib/format";

type Props = {
  summary: Summary | null;
  /** shown in place of the headline when /api/summary failed */
  summaryError?: React.ReactNode;
  /** the map block (map + legend, or its skeleton / error) */
  map: React.ReactNode;
};

export function Hero({ summary, summaryError, map }: Props) {
  return (
    <section className="hero-sky relative flex min-h-[100svh] flex-col overflow-hidden" aria-label="Overview">
      <RainLayer />
      <TopNav />
      <div className="hero-grid relative z-10 mx-auto w-full max-w-[1280px] flex-1 px-4 pt-4 pb-10 sm:px-6 lg:pt-0">
        <div className="area-head">
          <p className="text-[13px] font-semibold tracking-[0.14em] text-primary">MUMBAI MONSOON ROADS 2025</p>
          {summary ? (
            <h1 className="mt-3 text-[40px] leading-[1.05] font-semibold tracking-tight text-ink sm:text-5xl lg:text-[60px] lg:leading-[64px]">
              <CountUp value={summary.failed_spend_inr} className="text-scale-1" />{" "}
              <span className="block text-[24px] leading-tight font-medium text-ink sm:text-3xl lg:text-4xl lg:leading-[1.15]">
                of {inr(summary.total_spend_inr)} in repairs didn&apos;t hold for 30 days.
              </span>
            </h1>
          ) : summaryError ? (
            <div className="mt-3">{summaryError}</div>
          ) : (
            <div className="mt-3" aria-busy="true">
              <Skeleton className="h-14 w-72" />
              <Skeleton className="mt-3 h-8 w-full max-w-md" />
            </div>
          )}
        </div>

        <div className="area-bar">
          {summary ? <RupeeBar failedPct={summary.failed_pct} /> : <Skeleton className="h-28 w-full max-w-xl" />}
        </div>

        <div className="area-map">{map}</div>

        <div className="area-search">
          <HeroTrace />
        </div>
      </div>
    </section>
  );
}
