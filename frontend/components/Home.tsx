"use client";

import type { FeatureCollection } from "geojson";
import { ClipboardCheck, MapPinned, MessageSquareText } from "lucide-react";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { EntryCard } from "@/components/EntryCard";
import { ErrorBox } from "@/components/ErrorBox";
import { Hero } from "@/components/hero/Hero";
import { MapLegend } from "@/components/hero/MapLegend";
import { Reveal } from "@/components/Reveal";
import { StatCard } from "@/components/StatCard";
import { WardPanel } from "@/components/WardPanel";
import { WardPicker } from "@/components/WardPicker";
import { WardTile } from "@/components/WardTile";
import { Skeleton } from "@/components/ui/skeleton";
import { type Summary, type Ward, useApi } from "@/lib/api";
import { inr, num } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { rankBins } from "@/lib/scale";

const HeroMap = dynamic(() => import("@/components/hero/HeroMap"), {
  ssr: false,
  loading: () => <Skeleton className="h-[360px] w-full rounded-2xl sm:h-[460px] lg:h-[min(72vh,680px)]" />,
});

function Cards({ s }: { s: Summary }) {
  const t = useT();
  const reviewDlp = s.dlp_paid_total_inr - s.dlp_paid_liable_inr;
  return (
    <section aria-label="Key figures" className="grid grid-cols-[minmax(0,1fr)] gap-4 sm:grid-cols-3">
      <Reveal>
        <StatCard
          label={t("stat.warranty.label")}
          value={inr(s.dlp_paid_liable_inr)}
          note={t("stat.warranty.note", { n: num(s.dlp_paid_liable_count), m: inr(reviewDlp) })}
        />
      </Reveal>
      <Reveal delay={120}>
        <StatCard
          label={t("stat.rate.label")}
          value={inr(s.over_rate_excess_inr)}
          note={t("stat.rate.note", { n: num(s.over_rate_count) })}
        />
      </Reveal>
      <Reveal delay={240}>
        <StatCard
          label={t("stat.fatal.label")}
          value={num(s.road_defect_fatal)}
          note={t("stat.fatal.note", { n: num(s.road_defect_grievous) })}
        />
      </Reveal>
    </section>
  );
}

export function Home() {
  const t = useT();
  const summary = useApi<Summary>("/api/summary");
  const wards = useApi<Ward[]>("/api/wards");
  const geo = useApi<FeatureCollection>("/api/wards.geojson");
  const [selected, setSelected] = useState<string | null>(null);
  const [picker, setPicker] = useState<"explore" | "officer" | null>(null);

  const wardData = wards.state.status === "ready" ? wards.state.data : null;
  const bins = useMemo(() => (wardData && wardData.length ? rankBins(wardData) : null), [wardData]);
  const selectedWard = wardData?.find((w) => w.ward_code === selected) ?? null;
  const maxPct = useMemo(() => Math.max(1, ...(wardData ?? []).map((w) => w.failed_pct)), [wardData]);
  const tiles = useMemo(() => [...(wardData ?? [])].sort((a, b) => b.failed_pct - a.failed_pct), [wardData]);

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
        <section aria-label="Where to start" className="grid grid-cols-[minmax(0,1fr)] gap-4 sm:grid-cols-3">
          <Reveal>
            <EntryCard
              icon={MessageSquareText}
              title={t("entry.trace.title")}
              description={t("entry.trace.desc")}
              cta={t("entry.trace.cta")}
              href="/trace"
            />
          </Reveal>
          <Reveal delay={100}>
            <EntryCard
              icon={MapPinned}
              title={t("entry.explore.title")}
              description={t("entry.explore.desc")}
              cta={t("entry.explore.cta")}
              onClick={() => wardData && setPicker("explore")}
            />
          </Reveal>
          <Reveal delay={200}>
            <EntryCard
              icon={ClipboardCheck}
              title={t("entry.officer.title")}
              description={t("entry.officer.desc")}
              cta={t("entry.officer.cta")}
              onClick={() => wardData && setPicker("officer")}
            />
          </Reveal>
        </section>

        <div className="mt-10">{summary.state.status === "ready" && <Cards s={summary.state.data} />}</div>

        <section aria-labelledby="glance-h" className="mt-14">
          <h2 id="glance-h" className="text-2xl font-semibold tracking-tight">
            {t("home.glance.title")}
          </h2>
          <p className="mt-1 text-muted-foreground">{t("home.glance.sub")}</p>
          <div className="mt-4">
            {wardData && bins ? (
              <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-4 xl:grid-cols-6">
                {tiles.map((w) => (
                  <li key={w.ward_code} className="contents">
                    <WardTile ward={w} bins={bins} maxPct={maxPct} />
                  </li>
                ))}
              </ul>
            ) : wards.state.status === "error" ? (
              <ErrorBox message={wards.state.message} onRetry={wards.retry} />
            ) : (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6" aria-busy="true">
                {Array.from({ length: 12 }, (_, i) => (
                  <Skeleton key={i} className="h-[150px] rounded-2xl" />
                ))}
              </div>
            )}
          </div>
        </section>

        <footer className="mt-16 border-t pt-6 text-[13px] text-muted-foreground">
          {t("common.synthetic")} {t("common.fairNote")} Dataset: Follow the Rupee by Sumeet Doshi, CC BY 4.0.
          Basemap: Esri, HERE, Garmin, © OpenStreetMap contributors.
        </footer>
      </main>

      <WardPanel ward={selectedWard} onClose={() => setSelected(null)} />
      <WardPicker
        open={picker !== null}
        onOpenChange={(o) => !o && setPicker(null)}
        wards={wardData ?? []}
        mode={picker ?? "explore"}
      />
    </>
  );
}
