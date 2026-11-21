"use client";

import { useT } from "@/lib/i18n";
import { useInView } from "@/lib/useInView";
import { useReducedMotion } from "@/lib/useReducedMotion";

const TOTAL = 100;
const STAGGER_SPAN = 650; // ms across all failed tiles; each tile's drop is ~550ms => ~1.2s overall

/** 100 tiles = every ₹100 spent. The failed share cracks and drops away once. */
export function RupeeBar({ failedPct }: { failedPct: number }) {
  const failed = Math.max(0, Math.min(TOTAL, Math.round(failedPct)));
  const held = TOTAL - failed;
  const t = useT();
  const reduced = useReducedMotion();
  const [ref, inView] = useInView<HTMLDivElement>({ once: true, threshold: 0.5 });
  const drop = inView && !reduced;

  return (
    <figure className="m-0">
      <div
        ref={ref}
        role="img"
        aria-label={`Of every ₹100 spent on repairs, ₹${held} held and ₹${failed} didn't hold for 30 days.`}
        className="grid grid-cols-[repeat(20,minmax(0,1fr))] gap-[3px] sm:grid-cols-[repeat(25,minmax(0,1fr))]"
      >
        {Array.from({ length: TOTAL }, (_, i) => {
          const isFailed = i >= held;
          if (!isFailed) return <span key={i} className="aspect-square rounded-[3px] bg-scale-5" />;
          const k = i - held;
          return (
            <span key={i} className="tile-ghost relative aspect-square rounded-[3px]">
              {!reduced && (
                <span
                  className="tile-fail absolute inset-0 rounded-[3px]"
                  data-drop={drop}
                  style={{ ["--delay" as string]: `${Math.round((k / Math.max(failed - 1, 1)) * STAGGER_SPAN)}ms` }}
                />
              )}
            </span>
          );
        })}
      </div>
      <figcaption className="mt-3 text-[15px] text-hero-muted">
        {t("hero.bar.caption", { n: failed })}
      </figcaption>
    </figure>
  );
}
