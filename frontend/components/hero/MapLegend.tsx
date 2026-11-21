"use client";

import { useT } from "@/lib/i18n";
import { pct } from "@/lib/format";
import type { Bins } from "@/lib/scale";

export function MapLegend({ bins }: { bins: Bins }) {
  const t = useT();
  return (
    <div className="mt-3 text-[13px] text-hero-muted">
      <p className="font-medium text-ink">{t("map.title")}</p>
      <ul className="mt-1.5 grid grid-cols-5 gap-1" aria-label="Map legend: share of repair spend that didn't hold">
        {[...bins.ranges].reverse().map((r) => (
          <li key={r.token}>
            <span className="block h-3 rounded-sm border" style={{ background: `var(${r.token})` }} aria-hidden />
            <span className="mt-0.5 block text-center">
              {pct(r.min, 0)}
              {r.max - r.min >= 0.5 ? `–${pct(r.max, 0)}` : ""}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-1.5">{t("map.note")}</p>
    </div>
  );
}
