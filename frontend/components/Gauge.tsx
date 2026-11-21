import type { Band } from "@/lib/types";

const FILL: Record<Band, string> = {
  better: "var(--scale-5)", // teal: fine
  as_expected: "var(--hero-muted)", // grey: neutral
  worse: "var(--scale-1)", // red: worth checking
  neutral: "var(--hero-muted)",
};

/** A simple horizontal gauge: filled to `value`, a tick at `benchmark` (what we'd expect / typical). */
export function Gauge({
  value,
  benchmark,
  min,
  max,
  band,
  label,
}: {
  value: number;
  benchmark?: number | null;
  min: number;
  max: number;
  band: Band;
  label: string; // text alternative
}) {
  const pos = (v: number) => `${Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100))}%`;
  return (
    <div role="img" aria-label={label} className="relative h-3 w-full rounded-full bg-border">
      <div className="h-full rounded-full transition-[width] duration-700" style={{ width: pos(value), background: FILL[band] }} />
      {benchmark != null && (
        <span
          className="absolute top-1/2 h-5 w-0.5 -translate-y-1/2 rounded bg-ink"
          style={{ left: pos(benchmark) }}
          aria-hidden
        />
      )}
    </div>
  );
}
