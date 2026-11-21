import type { Ward } from "@/lib/api";

/** Map/table colour bins: rank-based quintiles of the SHARE of a ward's repair spend that didn't hold.
 *  Index 0 = highest share (deep red) … 4 = lowest share (teal). Never absolute ₹ (unfair to big spenders). */
export const BIN_TOKENS = ["--scale-1", "--scale-2", "--scale-3", "--scale-4", "--scale-5"] as const;

export type Bin = { index: number; token: (typeof BIN_TOKENS)[number] };

export type Bins = {
  byCode: Map<string, Bin>;
  /** share range (percent) covered by each bin, for the legend */
  ranges: { token: Bin["token"]; min: number; max: number }[];
  /** top 3 wards by share, in order */
  top3: string[];
};

export function rankBins(wards: Ward[]): Bins {
  const sorted = [...wards].sort((a, b) => b.failed_pct - a.failed_pct);
  const n = sorted.length;
  const byCode = new Map<string, Bin>();
  const ranges = BIN_TOKENS.map((token) => ({ token, min: Infinity, max: -Infinity }));
  sorted.forEach((w, rank) => {
    const index = Math.min(4, Math.floor((rank * 5) / n));
    byCode.set(w.ward_code, { index, token: BIN_TOKENS[index] });
    ranges[index].min = Math.min(ranges[index].min, w.failed_pct);
    ranges[index].max = Math.max(ranges[index].max, w.failed_pct);
  });
  return { byCode, ranges: ranges.filter((r) => r.min <= r.max), top3: sorted.slice(0, 3).map((w) => w.ward_code) };
}

export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
