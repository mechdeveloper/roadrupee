"use client";

import type { FeatureCollection } from "geojson";
import dynamic from "next/dynamic";
import { Landmark, MapPin } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ErrorBox } from "@/components/ErrorBox";
import { TrailFunnel } from "@/components/home/TrailFunnel";
import { AuditStrip } from "@/components/home/AuditStrip";
import { ContractorCards } from "@/components/home/ContractorCards";
import { HookBand } from "@/components/home/HookBand";
import { MoneyByMethod } from "@/components/home/MoneyByMethod";
import { MonsoonVsFailures } from "@/components/home/MonsoonVsFailures";
import { NextRupeeTop5 } from "@/components/home/NextRupeeTop5";
import { Section } from "@/components/home/Section";
import { WardLeague } from "@/components/home/WardLeague";
import { WorthChecking } from "@/components/home/WorthChecking";
import { MapLegend } from "@/components/hero/MapLegend";
import { WardPicker } from "@/components/WardPicker";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { type Summary, type Ward, useApi } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { rankBins } from "@/lib/scale";
import { wardHref } from "@/lib/wards";

const HeroMap = dynamic(() => import("@/components/hero/HeroMap"), {
  ssr: false,
  loading: () => <Skeleton className="h-[360px] w-full rounded-2xl sm:h-[440px] lg:h-[540px]" />,
});

export function Home() {
  const t = useT();
  const router = useRouter();
  const summary = useApi<Summary>("/api/summary");
  const wards = useApi<Ward[]>("/api/wards");
  const geo = useApi<FeatureCollection>("/api/wards.geojson");
  const [picker, setPicker] = useState<"explore" | "officer" | null>(null);

  const wardData = wards.state.status === "ready" ? wards.state.data : null;
  const bins = useMemo(() => (wardData && wardData.length ? rankBins(wardData) : null), [wardData]);
  const slugOf = useMemo(() => new Map((wardData ?? []).map((w) => [w.ward_code, w.slug])), [wardData]);
  const s = summary.state.status === "ready" ? summary.state.data : null;
  const auditTotal = s ? Object.values(s.flag_counts).reduce((n, r) => n + r.audit, 0) : 0;

  const mapNode =
    wards.state.status === "error" || geo.state.status === "error" ? (
      <ErrorBox message="The ward map is unavailable." onRetry={() => { wards.retry(); geo.retry(); }} />
    ) : wardData && bins && geo.state.status === "ready" ? (
      <>
        <HeroMap geo={geo.state.data} wards={wardData} bins={bins} onSelect={(code) => router.push(wardHref(slugOf.get(code) ?? ""))} />
        <MapLegend bins={bins} />
      </>
    ) : (
      <Skeleton className="h-[360px] w-full rounded-2xl sm:h-[440px] lg:h-[540px]" />
    );

  return (
    <>
      <HookBand
        summary={s}
        error={summary.state.status === "error" ? summary.state.message : undefined}
        retry={summary.retry}
      />

      <AuditStrip />
      <TrailFunnel />

      <main className="mx-auto w-full max-w-[1280px] flex-1 space-y-12 px-4 pt-8 pb-16 sm:px-6">
        <Section id="wards" title={t("home.q.wards")} seeAll="/wards">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
            <Button
              type="button"
              onClick={() => wardData && setPicker("explore")}
              className="h-12 w-full gap-2 px-6 text-base sm:w-auto"
            >
              <MapPin className="size-5" aria-hidden />
              {t("league.find")}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => wardData && setPicker("officer")}
              className="h-12 w-full gap-2 px-6 text-base sm:w-auto"
            >
              <Landmark className="size-5" aria-hidden />
              {t("league.officer")}
            </Button>
            <span className="text-[13px] text-muted-foreground sm:ml-2">{t("league.hint")}</span>
          </div>
          <div className="grid gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
            <div className="min-w-0">{mapNode}</div>
            <div className="min-w-0">
              {wardData && bins ? (
                <WardLeague wards={wardData} bins={bins} />
              ) : wards.state.status === "error" ? (
                <ErrorBox message={wards.state.message} onRetry={wards.retry} />
              ) : (
                <Skeleton className="h-[540px] w-full rounded-2xl" />
              )}
            </div>
          </div>
        </Section>

        <Section id="contractors" title={t("home.q.contractors")} seeAll="/contractors">
          <ContractorCards />
        </Section>

        <Section id="check" title={t("home.q.check")} seeAll="/audit" seeAllLabel={auditTotal ? t("home.seeAllFlags", { n: auditTotal }) : undefined}>
          <WorthChecking />
        </Section>

        <div className="grid gap-8 lg:grid-cols-2">
          <Section id="monsoon" title={t("home.q.monsoon")}>
            <MonsoonVsFailures />
          </Section>
          <Section id="next" title={t("home.q.next")} seeAll="/plan">
            <NextRupeeTop5 />
          </Section>
        </div>

        <Section id="money" title={t("home.q.money")} seeAll="/audit">
          <MoneyByMethod />
        </Section>

        <footer className="border-t pt-6 text-[13px] text-muted-foreground">
          {t("common.synthetic")} {t("common.fairNote")} Dataset: Follow the Rupee by Sumeet Doshi, CC BY 4.0. Basemap: Esri,
          HERE, Garmin, © OpenStreetMap contributors.
        </footer>
      </main>

      <WardPicker open={picker !== null} onOpenChange={(o) => !o && setPicker(null)} wards={wardData ?? []} mode={picker ?? "explore"} />
    </>
  );
}
