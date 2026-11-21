"use client";

import { useMemo } from "react";
import { ErrorBox } from "@/components/ErrorBox";
import { PageShell } from "@/components/PageShell";
import { WardLeague } from "@/components/home/WardLeague";
import { Skeleton } from "@/components/ui/skeleton";
import { type Ward, useApi } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { rankBins } from "@/lib/scale";

export function WardsPage() {
  const t = useT();
  const { state, retry } = useApi<Ward[]>("/api/wards");
  const bins = useMemo(() => (state.status === "ready" && state.data.length ? rankBins(state.data) : null), [state]);
  return (
    <PageShell title={t("page.wards.title")} subtitle={t("league.hint")}>
      {state.status === "ready" && bins ? (
        <WardLeague wards={state.data} bins={bins} tall />
      ) : state.status === "error" ? (
        <ErrorBox message={state.message} onRetry={retry} />
      ) : (
        <Skeleton className="h-[640px] w-full rounded-2xl" />
      )}
    </PageShell>
  );
}
