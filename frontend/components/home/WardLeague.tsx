"use client";

import { ArrowDown, ArrowUp, Info } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { VerdictChip } from "@/components/VerdictChip";
import type { Ward } from "@/lib/api";
import { inr, num, pct } from "@/lib/format";
import { type Key, useT } from "@/lib/i18n";
import { verdict } from "@/lib/plain";
import type { Bins } from "@/lib/scale";
import { wardHref } from "@/lib/wards";

type SortKey = "ward" | "spend" | "share" | "vs" | "flags";
const VS_ORDER = { worse: 0, "about as expected": 1, better: 2 } as const;
const COLS: { key: SortKey; label: Key; right?: boolean; info?: Key }[] = [
  { key: "ward", label: "league.col.ward" },
  { key: "spend", label: "league.col.spend", right: true },
  { key: "share", label: "league.col.share" },
  { key: "vs", label: "league.col.vs", info: "league.vs.info" },
  { key: "flags", label: "league.col.flags", right: true },
];

/** Sortable league table. A row opens the ward report. */
export function WardLeague({ wards, bins, tall = false }: { wards: Ward[]; bins: Bins; tall?: boolean }) {
  const t = useT();
  const router = useRouter();
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "share", dir: -1 });

  const rows = useMemo(() => {
    const val = (w: Ward): number | string =>
      ({
        ward: w.ward_code,
        spend: w.spend_inr / (w.budget_inr || 1),
        share: w.failed_pct,
        vs: VS_ORDER[verdict(w)],
        flags: w.flags_audit,
      })[sort.key];
    return [...wards].sort((a, b) => {
      const x = val(a);
      const y = val(b);
      return (typeof x === "string" ? x.localeCompare(y as string) : x - (y as number)) * sort.dir;
    });
  }, [wards, sort]);

  const maxShare = Math.max(1, ...wards.map((w) => w.failed_pct));
  const toggle = (key: SortKey) => setSort((s) => (s.key === key ? { key, dir: (s.dir * -1) as 1 | -1 } : { key, dir: key === "ward" ? 1 : -1 }));

  return (
    <div className={`overflow-auto rounded-2xl border bg-surface ${tall ? "" : "max-h-[540px]"}`}>
      <table className="w-full min-w-[700px] text-left text-sm">
        <caption className="sr-only">{t("league.hint")}</caption>
        <thead className="sticky top-0 z-20 bg-[var(--accent-soft)] text-[11px] tracking-normal text-muted-foreground uppercase shadow-[0_1px_0_var(--border)]">
          <tr>
            {COLS.map((c, ci) => (
              <th
                key={c.key}
                scope="col"
                aria-sort={sort.key === c.key ? (sort.dir === 1 ? "ascending" : "descending") : "none"}
                className={`p-0 align-middle font-semibold whitespace-nowrap ${c.right ? "text-right" : "text-left"} ${ci === 0 ? "sticky left-0 z-30 bg-[var(--accent-soft)]" : ""}`}
              >
                <div className={`flex min-h-11 items-center gap-1 px-2.5 ${c.right ? "justify-end" : ""}`}>
                  <button type="button" onClick={() => toggle(c.key)} className="inline-flex min-h-11 items-center gap-1 whitespace-nowrap uppercase">
                    {t(c.label)}
                    {sort.key === c.key && (sort.dir === 1 ? <ArrowUp className="size-3.5" aria-hidden /> : <ArrowDown className="size-3.5" aria-hidden />)}
                  </button>
                  {c.info && (
                    <span className="group relative inline-flex">
                      <button
                        type="button"
                        aria-label={t(c.info)}
                        aria-describedby={`tip-${c.key}`}
                        className="inline-flex size-5 items-center justify-center rounded-full text-muted-foreground hover:text-ink focus-visible:text-ink"
                      >
                        <Info className="size-3.5" aria-hidden />
                      </button>
                      <span
                        id={`tip-${c.key}`}
                        role="tooltip"
                        className="pointer-events-none absolute top-full right-0 z-40 mt-1 hidden w-64 translate-x-0 rounded-lg border bg-surface p-2.5 text-left text-[13px] font-normal tracking-normal text-ink normal-case whitespace-normal shadow-md group-focus-within:block group-hover:block"
                      >
                        {t(c.info)}
                      </span>
                    </span>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((w) => {
            const over = w.spend_inr > w.budget_inr;
            const token = bins.byCode.get(w.ward_code)?.token ?? "--scale-none";
            return (
              <tr
                key={w.ward_code}
                onClick={() => router.push(wardHref(w.slug))}
                className="cursor-pointer border-t hover:bg-background"
              >
                <td className="sticky left-0 z-10 bg-surface px-2.5 py-2 whitespace-nowrap">
                  <Link href={wardHref(w.slug)} onClick={(e) => e.stopPropagation()} className="flex min-h-9 items-center gap-2">
                    <span className="inline-block size-3 shrink-0 rounded-sm border" style={{ background: `var(${token})` }} aria-hidden />
                    <span>
                      <span className="font-semibold text-ink">{w.ward_code}</span>{" "}
                      <span className="text-muted-foreground">{w.ward_name.split(",")[0]}</span>
                    </span>
                  </Link>
                </td>
                <td className="px-2.5 py-2 text-right whitespace-nowrap tabular-nums">
                  <span className={over ? "font-semibold text-scale-1" : "text-ink"}>{inr(w.spend_inr)}</span>
                  <span className="text-muted-foreground"> / {inr(w.budget_inr)}</span>
                </td>
                <td className="px-2.5 py-2">
                  <span className="flex items-center gap-2">
                    <span className="w-11 font-semibold text-ink tabular-nums">{pct(w.failed_pct)}</span>
                    <span className="h-2 w-10 overflow-hidden rounded-full bg-border" aria-hidden>
                      <span className="block h-full rounded-full" style={{ width: `${(w.failed_pct / maxShare) * 100}%`, background: `var(${token})` }} />
                    </span>
                  </span>
                </td>
                <td className="px-2.5 py-2 whitespace-nowrap">
                  <VerdictChip ward={w} compact />
                </td>
                <td className="px-2.5 py-2 text-right font-semibold tabular-nums">{num(w.flags_audit)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
