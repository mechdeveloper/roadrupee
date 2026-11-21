"use client";

import { useMemo } from "react";
import { ErrorBox } from "@/components/ErrorBox";
import { VerdictChip } from "@/components/VerdictChip";
import { RainTimeline } from "@/components/ward/RainTimeline";
import { Skeleton } from "@/components/ui/skeleton";
import { type Ward, useApi } from "@/lib/api";
import { pct } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { verdict } from "@/lib/plain";
import type { WardTimeline } from "@/lib/types";
import { fmtDate } from "@/lib/wards";

const SENTENCE = {
  better: "held.sentence.better",
  "about as expected": "held.sentence.expected",
  worse: "held.sentence.worse",
} as const;

/** Monday of the week containing an ISO date (UTC). */
function weekStart(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return d.toISOString().slice(0, 10);
}

/** Tab b: Did the fixes hold? One big sentence with actual vs expected, then the monsoon timeline. */
export function HeldTab({ ward }: { ward: Ward }) {
  const t = useT();
  const { state, retry } = useApi<WardTimeline>(`/api/wards/${encodeURIComponent(ward.slug)}/timeline`);
  const v = verdict(ward);

  const weeks = useMemo(() => {
    if (state.status !== "ready") return [];
    const m = new Map<string, { rain: number; red: number; failed: number; hasRain: boolean }>();
    for (const d of state.data.days) {
      const k = weekStart(d.date);
      const w = m.get(k) ?? { rain: 0, red: 0, failed: 0, hasRain: false };
      if (d.rain_mm != null) {
        w.rain += d.rain_mm;
        w.hasRain = true;
      }
      if (d.alert === "Red") w.red += 1;
      w.failed += d.failed;
      m.set(k, w);
    }
    return [...m.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [state]);

  return (
    <div className="space-y-6">
      <section aria-labelledby="held-big" className="rounded-2xl border bg-surface p-5 sm:p-6">
        <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
          <p id="held-big">
            <span className="block text-5xl leading-none font-semibold tracking-tight text-scale-1">{pct(ward.reopen_observed_pct)}</span>
            <span className="mt-1 block text-[15px] text-muted-foreground">{t("held.bigLabel")}</span>
          </p>
          <VerdictChip ward={ward} />
        </div>
        <p className="mt-4 max-w-3xl text-[18px] leading-relaxed text-ink">
          {t(SENTENCE[v], { obs: pct(ward.reopen_observed_pct, 0), exp: pct(ward.reopen_expected_pct, 0) })}
        </p>
        <details className="mt-1 text-sm text-muted-foreground">
          <summary className="min-h-11 cursor-pointer py-2.5 font-medium text-primary">{t("held.how")}</summary>
          <p className="pb-1">
            {t("held.howBody", {
              exp: pct(ward.reopen_expected_pct),
              lo: pct(ward.reopen_ci_low_pct),
              hi: pct(ward.reopen_ci_high_pct),
            })}
          </p>
        </details>
      </section>

      <section aria-labelledby="held-tl" className="rounded-2xl border bg-surface p-5 sm:p-6">
        <h2 id="held-tl" className="text-2xl font-semibold tracking-tight">
          {t("held.timeline.title")}
        </h2>
        <div className="mt-3">
          {state.status === "loading" && <Skeleton className="h-[330px] w-full rounded-xl" aria-busy="true" />}
          {state.status === "error" && <ErrorBox message={state.message} onRetry={retry} />}
          {state.status === "ready" && (
            <>
              <RainTimeline timeline={state.data} />
              <details className="mt-3">
                <summary className="min-h-11 cursor-pointer py-2.5 font-medium text-primary">{t("held.table")}</summary>
                <div className="max-h-96 overflow-auto rounded-xl border">
                  <table className="w-full text-left text-sm">
                    <thead className="sticky top-0 bg-surface text-[13px] text-muted-foreground">
                      <tr>
                        <th className="p-2.5 font-medium">{t("held.col.week")}</th>
                        <th className="p-2.5 text-right font-medium">{t("held.col.rain")}</th>
                        <th className="p-2.5 text-right font-medium">{t("held.col.red")}</th>
                        <th className="p-2.5 text-right font-medium">{t("held.col.failed")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {weeks.map(([k, w]) => (
                        <tr key={k} className="border-t">
                          <td className="p-2.5">{fmtDate(k)}</td>
                          <td className="p-2.5 text-right">{w.hasRain ? w.rain.toFixed(0) : "—"}</td>
                          <td className="p-2.5 text-right">{w.red}</td>
                          <td className="p-2.5 text-right">{w.failed}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
