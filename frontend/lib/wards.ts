import type { Locality } from "@/lib/types";
import type { Ward } from "@/lib/api";

export function wardHref(slug: string, opts?: { mode?: "officer"; tab?: "money" | "held" | "check" | "next" }): string {
  const q = new URLSearchParams();
  if (opts?.tab) q.set("tab", opts.tab);
  if (opts?.mode) q.set("mode", opts.mode);
  const qs = q.toString();
  return `/ward/${slug}${qs ? `?${qs}` : ""}`;
}

const norm = (s: string) => s.normalize("NFC").toLowerCase().trim();

export type WardHit = { ward: Ward; via: string | null; score: number };

/** Search wards by code, name, areas, locality names and aliases (incl. Devanagari). */
export function searchWards(query: string, wards: Ward[], localities: Locality[], limit = 8): WardHit[] {
  const q = norm(query);
  if (!q) return [];
  const byCode = new Map(wards.map((w) => [w.ward_code, w]));
  const best = new Map<string, WardHit>();
  const consider = (ward: Ward | undefined, text: string, via: string | null) => {
    if (!ward) return;
    const t = norm(text);
    const score = t === q ? 3 : t.startsWith(q) ? 2 : t.includes(q) ? 1 : 0;
    if (!score) return;
    const prev = best.get(ward.ward_code);
    if (!prev || score > prev.score) best.set(ward.ward_code, { ward, via, score });
  };
  for (const w of wards) {
    consider(w, w.ward_code, null);
    consider(w, w.ward_name, null);
    for (const l of w.localities) consider(w, l, l);
  }
  for (const l of localities) {
    const ward = byCode.get(l.ward_code);
    consider(ward, l.locality, l.locality);
    for (const a of l.aliases) consider(ward, a, `${a} (${l.locality})`);
  }
  return [...best.values()]
    .sort((a, b) => b.score - a.score || a.ward.ward_code.localeCompare(b.ward.ward_code))
    .slice(0, limit);
}
