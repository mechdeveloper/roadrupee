/** Diverging bins around the city-wide failed-spend share. Thresholds in percentage points. */
export const BINS = [
  { token: "--scale-1", label: "8+ pts above city average", test: (d: number) => d >= 8 },
  { token: "--scale-2", label: "3–8 pts above", test: (d: number) => d >= 3 },
  { token: "--scale-3", label: "Within 3 pts of average", test: (d: number) => d > -3 },
  { token: "--scale-4", label: "3–8 pts below", test: (d: number) => d > -8 },
  { token: "--scale-5", label: "8+ pts below", test: () => true },
] as const;

export function binFor(wardPct: number, cityPct: number) {
  const d = wardPct - cityPct;
  return BINS.find((b) => b.test(d)) ?? BINS[2];
}

export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
