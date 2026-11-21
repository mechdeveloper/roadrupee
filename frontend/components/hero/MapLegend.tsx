import { pct } from "@/lib/format";
import type { Bins } from "@/lib/scale";

export function MapLegend({ bins }: { bins: Bins }) {
  return (
    <div className="mt-3 text-[13px] text-hero-muted">
      <div className="flex items-center justify-between font-medium text-ink">
        <span>Higher share didn&apos;t hold</span>
        <span aria-hidden>←  →</span>
        <span>Held better</span>
      </div>
      <ul className="mt-1.5 grid grid-cols-5 gap-1" aria-label="Map legend: share of repair spend that didn't hold">
        {bins.ranges.map((r) => (
          <li key={r.token}>
            <span className="block h-3 rounded-sm border" style={{ background: `var(${r.token})` }} aria-hidden />
            <span className="mt-0.5 block text-center">
              {pct(r.max, 0)}
              {r.max - r.min >= 0.5 ? `–${pct(r.min, 0)}` : ""}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-1.5">
        Share of each ward&apos;s repair spend on fixes reopened within 30 days. Click a ward for details. Ward
        boundaries are approximate.
      </p>
    </div>
  );
}
