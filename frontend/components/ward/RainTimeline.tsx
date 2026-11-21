"use client";

import { useMemo } from "react";
import { Bar, CartesianGrid, ComposedChart, ReferenceArea, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import { useT } from "@/lib/i18n";
import type { WardTimeline } from "@/lib/types";
import { useMediaQuery } from "@/lib/useMediaQuery";
import { useReducedMotion } from "@/lib/useReducedMotion";
import { fmtDate } from "@/lib/wards";

type Row = {
  date: string;
  rain: number | null;
  alert: string | null;
  failed: number;
  ids: string[];
  dot: number | null;
};

const TICK = { fill: "var(--muted)", fontSize: 12 };
const MONTH = new Intl.DateTimeFormat("en-IN", { month: "short", timeZone: "UTC" });

/** A failure dot: size grows with the number of repairs that finished that day and later failed. */
function Dot(props: { cx?: number; cy?: number; payload?: Row }) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload || !payload.failed) return null;
  return <circle cx={cx} cy={cy} r={3.5 + Math.min(payload.failed, 4) * 1.5} fill="var(--scale-1)" stroke="var(--surface)" strokeWidth={1.5} />;
}

function Tip({ active, payload }: { active?: boolean; payload?: { payload: Row }[] }) {
  const t = useT();
  if (!active || !payload?.length) return null;
  const r = payload[0].payload;
  return (
    <div className="rounded-lg border bg-surface p-2.5 text-[13px] shadow-md">
      <p className="font-semibold text-ink">{fmtDate(r.date)}</p>
      <p className="text-muted-foreground">
        {r.rain == null ? t("held.tip.none") : t("held.tip.rain", { mm: r.rain.toFixed(0) })}
        {r.alert && r.alert !== "Green" ? ` · ${t("held.tip.alert", { level: r.alert })}` : ""}
      </p>
      {r.failed > 0 && (
        <p className="mt-1 font-medium text-scale-1">
          {t("held.tip.failed", { n: r.failed })}
          <span className="block font-mono text-[12px] font-normal text-muted-foreground">{r.ids.slice(0, 3).join(", ")}</span>
        </p>
      )}
    </div>
  );
}

/** City-wide variant: too many failures per day for dots, so two aligned single-axis charts (rain above, failures below). */
function CityCharts({ rows, redDays, monthTicks, noDataFrom, last, mobile, reduced }: {
  rows: Row[]; redDays: string[]; monthTicks: string[]; noDataFrom: string | null; last?: string; mobile: boolean; reduced: boolean;
}) {
  const areas = (
    <>
      {noDataFrom && last && <ReferenceArea yAxisId="y" x1={noDataFrom} x2={last} fill="var(--scale-none)" fillOpacity={1} />}
      {redDays.map((d) => (
        <ReferenceArea key={d} yAxisId="y" x1={d} x2={d} fill="var(--scale-1)" fillOpacity={0.16} />
      ))}
    </>
  );
  const axisX = (show: boolean) => (
    <XAxis
      dataKey="date"
      ticks={monthTicks}
      tickFormatter={(d: string) => MONTH.format(new Date(`${d}T00:00:00Z`))}
      tick={show ? TICK : false}
      height={show ? 24 : 4}
      tickLine={false}
      axisLine={{ stroke: "var(--border)" }}
      interval={0}
    />
  );
  return (
    <>
      <ResponsiveContainer width="100%" height={mobile ? 130 : 150}>
        <ComposedChart data={rows} syncId="city" margin={{ top: 6, right: 4, left: -12, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          {axisX(false)}
          <YAxis yAxisId="y" tick={TICK} tickLine={false} axisLine={false} width={44} />
          {areas}
          <Bar yAxisId="y" dataKey="rain" fill="var(--chart-rain)" isAnimationActive={!reduced} />
          <Tooltip content={<Tip />} cursor={{ fill: "var(--border)", fillOpacity: 0.5 }} />
        </ComposedChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height={mobile ? 120 : 140}>
        <ComposedChart data={rows} syncId="city" margin={{ top: 6, right: 4, left: -12, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          {axisX(true)}
          <YAxis yAxisId="y" tick={TICK} tickLine={false} axisLine={false} width={44} allowDecimals={false} />
          {areas}
          <Bar yAxisId="y" dataKey="failed" fill="var(--scale-1)" isAnimationActive={!reduced} />
          <Tooltip content={<Tip />} cursor={{ fill: "var(--border)", fillOpacity: 0.5 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </>
  );
}

/** Daily rain bars, red-alert days highlighted, repair-failure dots on top. Tokens only. */
export function RainTimeline({ timeline }: { timeline: WardTimeline }) {
  const t = useT();
  const reduced = useReducedMotion();
  const mobile = useMediaQuery("(max-width: 639px)");

  const { rows, redDays, monthTicks, noDataFrom, last } = useMemo(() => {
    const rows: Row[] = timeline.days.map((d) => ({
      date: d.date,
      rain: d.rain_mm,
      alert: d.alert,
      failed: d.failed,
      ids: d.failed_wo_ids,
      dot: d.failed > 0 ? 1 : null,
    }));
    return {
      rows,
      redDays: rows.filter((r) => r.alert === "Red").map((r) => r.date),
      monthTicks: rows.filter((r, i) => r.date.endsWith("-01") || i === 0).map((r) => r.date),
      noDataFrom: rows.find((r) => r.rain == null)?.date ?? null,
      last: rows[rows.length - 1]?.date,
    };
  }, [timeline]);

  const summary = t("held.facts", { red: timeline.red_alert_days, failed: timeline.failed_total });

  return (
    <div>
      <div role="img" aria-label={`${t("held.timeline.title")}. ${summary}`}>
        {timeline.ward_code === "ALL" ? (
          <CityCharts rows={rows} redDays={redDays} monthTicks={monthTicks} noDataFrom={noDataFrom} last={last} mobile={mobile} reduced={reduced} />
        ) : (
        <ResponsiveContainer width="100%" height={mobile ? 250 : 330}>
          <ComposedChart data={rows} margin={{ top: 8, right: 4, left: -12, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis
              dataKey="date"
              ticks={monthTicks}
              tickFormatter={(d: string) => MONTH.format(new Date(`${d}T00:00:00Z`))}
              tick={TICK}
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              interval={0}
            />
            <YAxis yAxisId="rain" tick={TICK} tickLine={false} axisLine={false} width={44} />
            <YAxis yAxisId="dots" hide domain={[0, 1.12]} />
            {noDataFrom && last && (
              <ReferenceArea yAxisId="rain" x1={noDataFrom} x2={last} fill="var(--scale-none)" fillOpacity={1} />
            )}
            {redDays.map((d) => (
              <ReferenceArea key={d} yAxisId="rain" x1={d} x2={d} fill="var(--scale-1)" fillOpacity={0.16} />
            ))}
            <Bar yAxisId="rain" dataKey="rain" fill="var(--chart-rain)" isAnimationActive={!reduced} />
            <Scatter yAxisId="dots" dataKey="dot" shape={<Dot />} isAnimationActive={!reduced} />
            <Tooltip content={<Tip />} cursor={{ fill: "var(--border)", fillOpacity: 0.5 }} />
          </ComposedChart>
        </ResponsiveContainer>
        )}
      </div>

      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-[13px] text-ink">
        <li className="flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-sm" style={{ background: "var(--chart-rain)" }} aria-hidden />
          {t("held.legend.rain")}
        </li>
        <li className="flex items-center gap-2">
          <span className={`inline-block size-3 ${timeline.ward_code === "ALL" ? "rounded-sm" : "rounded-full"}`} style={{ background: "var(--scale-1)" }} aria-hidden />
          {t("held.legend.fail")}
        </li>
        <li className="flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-sm" style={{ background: "color-mix(in srgb, var(--scale-1) 16%, var(--surface))", outline: "1px solid var(--scale-1)" }} aria-hidden />
          {t("held.legend.red")}
        </li>
        {noDataFrom && (
          <li className="flex items-center gap-2">
            <span className="inline-block h-3 w-3 rounded-sm border" style={{ background: "var(--scale-none)" }} aria-hidden />
            {t("held.legend.nodata")}
          </li>
        )}
      </ul>
      <p className="mt-2 text-[13px] text-muted-foreground">{summary}</p>
      <p className="mt-1 text-[13px] text-muted-foreground">{t(timeline.ward_code === "ALL" ? "held.barNote" : "held.dotNote")}</p>
    </div>
  );
}
