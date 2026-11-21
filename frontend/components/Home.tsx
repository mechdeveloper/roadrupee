"use client";

import type { FeatureCollection } from "geojson";
import dynamic from "next/dynamic";
import { ErrorBox } from "@/components/ErrorBox";
import { StatCard, StatCardSkeleton } from "@/components/StatCard";
import { TraceBox } from "@/components/TraceBox";
import { Skeleton } from "@/components/ui/skeleton";
import { type Summary, type Ward, useApi } from "@/lib/api";
import { inr, num, pct } from "@/lib/format";
import { BINS, binFor } from "@/lib/scale";

const WardMap = dynamic(() => import("@/components/WardMap"), {
  ssr: false,
  loading: () => <Skeleton className="h-[560px] w-full rounded-xl" />,
});

function Hero({ s }: { s: Summary }) {
  return (
    <header className="pt-10 pb-8 sm:pt-16">
      <p className="text-sm font-medium text-primary">RoadRupee · Mumbai monsoon roads</p>
      <h1 className="mt-3 max-w-4xl text-4xl leading-[1.1] font-semibold tracking-tight text-ink sm:text-[56px] sm:leading-[60px]">
        <span className="text-primary">{inr(s.failed_spend_inr)}</span> of the {inr(s.total_spend_inr)}{" "}
        spent on monsoon road repairs didn&apos;t hold for 30 days.
      </h1>
      <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
        That is {pct(s.failed_pct)} of the money: {num(s.failed_work_orders)} of {num(s.work_orders)}{" "}
        repair jobs had to be reopened. Where did the repair money go, and did the fix hold?
      </p>
    </header>
  );
}

function Cards({ s }: { s: Summary }) {
  const reviewDlp = s.dlp_paid_total_inr - s.dlp_paid_liable_inr;
  return (
    <section aria-label="Key figures" className="grid grid-cols-[minmax(0,1fr)] gap-4 sm:grid-cols-3">
      <StatCard
        label="Paid on roads still under warranty (DLP)"
        value={inr(s.dlp_paid_liable_inr)}
        note={`${num(s.dlp_paid_liable_count)} surface repairs the original contractor may owe at no cost. Another ${inr(reviewDlp)} on DLP roads is worth reviewing.`}
      />
      <StatCard
        label="Billed above the rate card"
        value={inr(s.over_rate_excess_inr)}
        note={`Excess on ${num(s.over_rate_count)} jobs billed over 1.5× the standard rate. Normal ±30% variation is not counted.`}
      />
      <StatCard
        label="Fatal accidents linked to road defects"
        value={num(s.road_defect_fatal)}
        note={`Potholes, waterlogging, open chambers (plus ${num(s.road_defect_grievous)} with grievous injuries).`}
      />
    </section>
  );
}

function Legend() {
  return (
    <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-muted-foreground" aria-label="Map legend">
      {BINS.map((b) => (
        <li key={b.token} className="flex items-center gap-2">
          <span
            className="inline-block size-3 rounded-sm border"
            style={{ background: `var(${b.token})` }}
            aria-hidden
          />
          {b.label}
        </li>
      ))}
    </ul>
  );
}

function WardTable({ wards, cityPct }: { wards: Ward[]; cityPct: number }) {
  const rows = [...wards].sort((a, b) => b.failed_spend_inr - a.failed_spend_inr);
  return (
    <div className="overflow-x-auto rounded-xl border bg-surface">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Wards ranked by money that did not hold</caption>
        <thead className="border-b text-[13px] text-muted-foreground">
          <tr>
            <th className="p-3 font-medium">Ward</th>
            <th className="p-3 text-right font-medium">Didn&apos;t hold</th>
            <th className="p-3 text-right font-medium">Share</th>
            <th className="p-3 text-right font-medium">Budget left</th>
            <th className="p-3 text-right font-medium">Worth checking</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((w) => (
            <tr key={w.ward_code} className="border-b last:border-0">
              <td className="p-3">
                <span
                  className="mr-2 inline-block size-3 rounded-sm border align-middle"
                  style={{ background: `var(${binFor(w.failed_pct, cityPct).token})` }}
                  aria-hidden
                />
                <span className="font-medium">{w.ward_code}</span>{" "}
                <span className="text-muted-foreground">{w.ward_name}</span>
              </td>
              <td className="p-3 text-right">{inr(w.failed_spend_inr)}</td>
              <td className="p-3 text-right">{pct(w.failed_pct)}</td>
              <td className="p-3 text-right">{inr(w.remaining_budget_inr)}</td>
              <td className="p-3 text-right">{num(w.flags_audit)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Home() {
  const summary = useApi<Summary>("/api/summary");
  const wards = useApi<Ward[]>("/api/wards");
  const geo = useApi<FeatureCollection>("/api/wards.geojson");

  return (
    <main className="mx-auto w-full max-w-[1100px] flex-1 px-4 pb-16 sm:px-6">
      {summary.state.status === "ready" ? (
        <Hero s={summary.state.data} />
      ) : summary.state.status === "error" ? (
        <div className="py-16">
          <ErrorBox message={summary.state.message} onRetry={summary.retry} />
        </div>
      ) : (
        <div className="pt-16 pb-8" aria-busy="true">
          <Skeleton className="h-14 w-full max-w-3xl" />
          <Skeleton className="mt-3 h-14 w-2/3" />
        </div>
      )}

      {summary.state.status === "ready" ? (
        <Cards s={summary.state.data} />
      ) : summary.state.status === "loading" ? (
        <div className="grid grid-cols-[minmax(0,1fr)] gap-4 sm:grid-cols-3">
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>
      ) : null}

      <section aria-labelledby="map-h" className="mt-12">
        <h2 id="map-h" className="text-2xl font-semibold tracking-tight">
          Money that didn&apos;t hold, by ward
        </h2>
        <p className="mt-1 text-muted-foreground">
          Share of each ward&apos;s repair spend on fixes reopened within 30 days, compared with the
          city average.
        </p>
        <div className="mt-4">
          {wards.state.status === "error" || geo.state.status === "error" ? (
            <ErrorBox
              message="The ward data is unavailable."
              onRetry={() => {
                wards.retry();
                geo.retry();
              }}
            />
          ) : wards.state.status === "ready" && geo.state.status === "ready" && summary.state.status === "ready" ? (
            wards.state.data.length === 0 ? (
              <p className="rounded-xl border bg-surface p-5 text-muted-foreground">
                No ward data yet. Check that the dataset is loaded on the server.
              </p>
            ) : (
              <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
                <div>
                  <WardMap geo={geo.state.data} wards={wards.state.data} cityPct={summary.state.data.failed_pct} />
                  <Legend />
                </div>
                <div>
                  <h3 className="mb-3 text-lg font-semibold">Wards, ranked</h3>
                  <WardTable wards={wards.state.data} cityPct={summary.state.data.failed_pct} />
                </div>
              </div>
            )
          ) : (
            <Skeleton className="h-[560px] w-full rounded-xl" />
          )}
        </div>
      </section>

      <div className="mt-12">
        <TraceBox />
      </div>

      <footer className="mt-16 border-t pt-6 text-[13px] text-muted-foreground">
        All data is synthetic and all contractors are fictional. Figures flag jobs that are worth
        checking, not conclusions about anyone. Dataset: Follow the Rupee by Sumeet Doshi, CC BY 4.0.
      </footer>
    </main>
  );
}
