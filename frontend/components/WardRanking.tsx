"use client";

import type { Ward } from "@/lib/api";
import { inr, num, pct } from "@/lib/format";
import type { Bins } from "@/lib/scale";

export function WardRanking({
  wards,
  bins,
  onSelect,
}: {
  wards: Ward[];
  bins: Bins;
  onSelect: (code: string) => void;
}) {
  const rows = [...wards].sort((a, b) => b.failed_pct - a.failed_pct);
  return (
    <div className="overflow-x-auto rounded-xl border bg-surface">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">
          Wards ranked by the share of repair spend that didn&apos;t hold. Select a ward for details.
        </caption>
        <thead className="border-b text-[13px] text-muted-foreground">
          <tr>
            <th className="p-3 font-medium">Ward</th>
            <th className="p-3 text-right font-medium">Share that didn&apos;t hold</th>
            <th className="p-3 text-right font-medium">₹ that didn&apos;t hold</th>
            <th className="p-3 text-right font-medium">Budget left</th>
            <th className="p-3 text-right font-medium">Worth checking</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((w) => (
            <tr key={w.ward_code} className="border-b last:border-0 hover:bg-background">
              <td className="p-0">
                <button
                  type="button"
                  onClick={() => onSelect(w.ward_code)}
                  className="flex min-h-11 w-full items-center gap-2 p-3 text-left"
                  aria-label={`Open details for ward ${w.ward_code}, ${w.ward_name}`}
                >
                  <span
                    className="inline-block size-3 shrink-0 rounded-sm border"
                    style={{ background: `var(${bins.byCode.get(w.ward_code)?.token ?? "--scale-none"})` }}
                    aria-hidden
                  />
                  <span>
                    <span className="font-medium">{w.ward_code}</span>{" "}
                    <span className="text-muted-foreground">{w.ward_name}</span>
                  </span>
                </button>
              </td>
              <td className="p-3 text-right font-medium">{pct(w.failed_pct)}</td>
              <td className="p-3 text-right">{inr(w.failed_spend_inr)}</td>
              <td className="p-3 text-right">{inr(w.remaining_budget_inr)}</td>
              <td className="p-3 text-right">{num(w.flags_audit)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
