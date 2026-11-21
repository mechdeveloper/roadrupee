"use client";

import { ArrowDown, ArrowUp } from "lucide-react";
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
const COLS: { key: SortKey; label: Key; right?: boolean }[] = [
  { key: "ward", label: "league.col.ward" },
  { key: "spend", label: "league.col.spend" },
  { key: "share", label: "league.col.share" },
  { key: "vs", label: "league.col.vs" },
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
      <table className="w-full min-w-[620px] text-left text-sm">
        <caption className="sr-only">{t("league.hint")}</caption>
        <thead className="sticky top-0 z-10 bg-surface text-[13px] text-muted-foreground shadow-[0_1px_0_var(--border)]">
          <tr>
            {COLS.map((c) => (
              <th
                key={c.key}
                scope="col"
                aria-sort={sort.key === c.key ? (sort.dir === 1 ? "ascending" : "descending") : "none"}
                className={`p-0 font-medium ${c.right ? "text-right" : ""}`}
              >
                <button type="button" onClick={() => toggle(c.key)} className={`flex min-h-11 w-full items-center gap-1 px-3 ${c.right ? "justify-end" : ""}`}>
                  {t(c.label)}
                  {sort.key === c.key && (sort.dir === 1 ? <ArrowUp className="size-3.5" aria-hidden /> : <ArrowDown className="size-3.5" aria-hidden />)}
                </button>
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
                <td className="px-3 py-2">
                  <Link href={wardHref(w.slug)} onClick={(e) => e.stopPropagation()} className="flex min-h-9 items-center gap-2">
                    <span className="inline-block size-3 shrink-0 rounded-sm border" style={{ background: `var(${token})` }} aria-hidden />
                    <span>
                      <span className="font-semibold text-ink">{w.ward_code}</span>{" "}
                      <span className="text-muted-foreground">{w.ward_name.split(",")[0]}</span>
                    </span>
                  </Link>
                </td>
                <td className="px-3 py-2">
                  <span className={over ? "font-semibold text-scale-1" : "text-ink"}>{inr(w.spend_inr)}</span>
                  <span className="text-muted-foreground"> / {inr(w.budget_inr)}</span>
                </td>
                <td className="px-3 py-2">
                  <span className="flex items-center gap-2">
                    <span className="w-12 font-semibold text-ink">{pct(w.failed_pct)}</span>
                    <span className="h-2 w-24 overflow-hidden rounded-full bg-border" aria-hidden>
                      <span className="block h-full rounded-full" style={{ width: `${(w.failed_pct / maxShare) * 100}%`, background: `var(${token})` }} />
                    </span>
                  </span>
                </td>
                <td className="px-3 py-2">
                  <VerdictChip ward={w} compact />
                </td>
                <td className="px-3 py-2 text-right font-semibold">{num(w.flags_audit)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
