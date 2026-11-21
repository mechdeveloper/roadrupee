"use client";

import { ErrorBox } from "@/components/ErrorBox";
import { RainTimeline } from "@/components/ward/RainTimeline";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api";
import type { WardTimeline } from "@/lib/types";

/** City-wide daily rain with every repair that later failed. Same chart as the ward page. */
export function MonsoonVsFailures() {
  const { state, retry } = useApi<WardTimeline>("/api/home/monsoon");
  if (state.status === "error") return <ErrorBox message={state.message} onRetry={retry} />;
  if (state.status === "loading") return <Skeleton className="h-[330px] w-full rounded-2xl" aria-busy="true" />;
  return (
    <div className="rounded-2xl border bg-surface p-4 sm:p-5">
      <RainTimeline timeline={state.data} />
    </div>
  );
}
