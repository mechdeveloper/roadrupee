"use client";

import { useEffect, useState } from "react";
import { inr } from "@/lib/format";
import { useReducedMotion } from "@/lib/useReducedMotion";

const DURATION = 1400;
const ease = (t: number) => 1 - Math.pow(1 - t, 3);

/** Counts up to `value` (rupees) and ends on exactly inr(value). Unit stays "Cr" while counting. */
export function CountUp({ value, className }: { value: number; className?: string }) {
  const reduced = useReducedMotion();
  const [t, setT] = useState(0);

  useEffect(() => {
    if (reduced) return;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min((now - start) / DURATION, 1);
      setT(p);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [reduced, value]);

  const done = reduced || t >= 1;
  const text = done
    ? inr(value)
    : value >= 1e7
      ? `₹${((value * ease(t)) / 1e7).toFixed(2)} Cr`
      : inr(value * ease(t));

  return (
    <span className={className} aria-label={inr(value)} role="text">
      <span aria-hidden>{text}</span>
    </span>
  );
}
