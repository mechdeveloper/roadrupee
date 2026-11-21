"use client";

import type { FeatureCollection } from "geojson";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { ErrorBox } from "@/components/ErrorBox";
import { Hero } from "@/components/hero/Hero";
import { MapLegend } from "@/components/hero/MapLegend";
import { Reveal } from "@/components/Reveal";
import { StatCard } from "@/components/StatCard";
import { WardPanel } from "@/components/WardPanel";
import { WardRanking } from "@/components/WardRanking";
import { Skeleton } from "@/components/ui/skeleton";
import { type Summary, type Ward, useApi } from "@/lib/api";
import { inr, num } from "@/lib/format";
import { rankBins } from "@/lib/scale";

const HeroMap = dynamic(() => import("@/components/hero/HeroMap"), {
  ssr: false,
  loading: () => <Skeleton className="h-[360px] w-full rounded-2xl sm:h-[460px] lg:h-[min(72vh,680px)]" />,
});

function Cards({ s }: { s: Summary }) {
  const reviewDlp = s.dlp_paid_total_inr - s.dlp_paid_liable_inr;
  return (
    <section aria-label="Key figures" className="grid grid-cols-[minmax(0,1fr)] gap-4 sm:grid-cols-3">
      <Reveal>
        <StatCard
          label="Paid for repairs still under the contractor's warranty"
          value={inr(s.dlp_paid_liable_inr)}
          note={`${num(s.dlp_paid_liable_count)} surface repairs the original contractor may owe at no cost. Another ${inr(reviewDlp)} on warranty roads is worth reviewing.`}
        />
      </Reveal>
      <Reveal delay={120}>
        <StatCard
          label="Billed above the standard rate"
          value={inr(s.over_rate_excess_inr)}
          note={`Extra charged on ${num(s.over_rate_count)} jobs billed over 1.5× the standard rate. Normal ±30% variation is not counted.`}
        />
      </Reveal>
      <Reveal delay={240}>
        <StatCard
          label="Fatal accidents linked to potholes, waterlogging and open chambers"
          value={num(s.road_defect_fatal)}
          note={`Plus ${num(s.road_defect_grievous)} accidents with grievous injuries.`}
        />
      </Reveal>
    </section>
  );
}

export function Home() {
  const summary = useApi<Summary>("/api/summary");
  const wards = useApi<Ward[]>("/api/wards");
  const geo = useApi<FeatureCollection>("/api/wards.geojson");
  const [selected, setSelected] = useState<string | null>(null);

  const wardData = wards.state.status === "ready" ? wards.state.data : null;
  const bins = useMemo(() => (wardData && wardData.length ? rankBins(wardData) : null), [wardData]);
  const selectedWard = wardData?.find((w) => w.ward_code === selected) ?? null;

  const mapNode =
    wards.state.status === "error" || geo.state.status === "error" ? (
      <ErrorBox
        message="The ward map is unavailable."
        onRetry={() => {
          wards.retry();
          geo.retry();
        }}
      />
    ) : wardData && bins && geo.state.status === "ready" ? (
      <>
        <HeroMap geo={geo.state.data} wards={wardData} bins={bins} onSelect={setSelected} />
        <MapLegend bins={bins} />
      </>
    ) : wardData && wardData.length === 0 ? (
      <p className="rounded-xl border bg-surface p-5 text-muted-foreground">
        No ward data yet. Check that the dataset is loaded on the server.
      </p>
    ) : (
      <Skeleton className="h-[360px] w-full rounded-2xl sm:h-[460px] lg:h-[min(72vh,680px)]" />
    );

  return (
    <>
      <Hero
        summary={summary.state.status === "ready" ? summary.state.data : null}
        summaryError={
          summary.state.status === "error" ? (
            <ErrorBox message={summary.state.message} onRetry={summary.retry} />
          ) : undefined
        }
        map={mapNode}
      />

      <main className="mx-auto w-full max-w-[1100px] flex-1 px-4 pt-12 pb-16 sm:px-6">
        {summary.state.status === "ready" && <Cards s={summary.state.data} />}

        <section aria-labelledby="rank-h" className="mt-14">
          <h2 id="rank-h" className="text-2xl font-semibold tracking-tight">
            Wards, ranked by the share that didn&apos;t hold
          </h2>
          <p className="mt-1 text-muted-foreground">
            Ranked by share of each ward&apos;s own repair spend, so wards that spend more aren&apos;t singled out
            unfairly. Select a ward for details.
          </p>
          <div className="mt-4">
            {wardData && bins ? (
              <WardRanking wards={wardData} bins={bins} onSelect={setSelected} />
            ) : wards.state.status === "error" ? (
              <ErrorBox message={wards.state.message} onRetry={wards.retry} />
            ) : (
              <Skeleton className="h-64 w-full rounded-xl" />
            )}
          </div>
        </section>

        <footer className="mt-16 border-t pt-6 text-[13px] text-muted-foreground">
          All data is synthetic and all contractors are fictional. Figures flag jobs that are worth checking, not
          conclusions about anyone. Dataset: Follow the Rupee by Sumeet Doshi, CC BY 4.0. Basemap: Esri, HERE, Garmin, © OpenStreetMap contributors.
        </footer>
      </main>

      <WardPanel ward={selectedWard} onClose={() => setSelected(null)} />
    </>
  );
}
