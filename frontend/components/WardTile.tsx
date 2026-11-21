"use client";

import Link from "next/link";
import { VerdictChip } from "@/components/VerdictChip";
import type { Ward } from "@/lib/api";
import { pct } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { Bins } from "@/lib/scale";
import { wardHref } from "@/lib/wards";

/** One ward at a glance: name, share that didn't hold as a mini bar, verdict chip. Opens the ward report. */
export function WardTile({ ward, bins, maxPct }: { ward: Ward; bins: Bins; maxPct: number }) {
  const t = useT();
  const token = bins.byCode.get(ward.ward_code)?.token ?? "--scale-none";
  return (
    <Link
      href={wardHref(ward.slug)}
      className="flex min-h-[148px] flex-col rounded-2xl border bg-surface p-4 shadow-sm transition-shadow hover:shadow-md"
      aria-label={`${t("picker.ward", { code: ward.ward_code })}, ${ward.ward_name}: ${pct(ward.failed_pct)} ${t("tile.didnthold")}`}
    >
      <span className="flex items-start justify-between gap-2">
        <span className="text-xl font-semibold tracking-tight text-ink">{ward.ward_code}</span>
        <VerdictChip ward={ward} />
      </span>
      <span className="mt-0.5 line-clamp-2 text-[13px] text-muted-foreground">{ward.ward_name}</span>
      <span className="mt-auto block pt-3">
        <span className="text-2xl font-semibold text-ink">{pct(ward.failed_pct)}</span>{" "}
        <span className="text-[13px] text-muted-foreground">{t("tile.didnthold")}</span>
        <span className="mt-1.5 block h-2 w-full overflow-hidden rounded-full bg-border" aria-hidden>
          <span
            className="block h-full rounded-full"
            style={{ width: `${(ward.failed_pct / maxPct) * 100}%`, background: `var(${token})` }}
          />
        </span>
      </span>
    </Link>
  );
}
