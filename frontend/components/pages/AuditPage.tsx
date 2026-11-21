"use client";

import { Download } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ClaudeVerdictChip } from "@/components/ClaudeVerdictChip";
import { Chip } from "@/components/Chip";
import { ErrorBox } from "@/components/ErrorBox";
import { PageShell } from "@/components/PageShell";
import { RULE_ICON } from "@/components/home/WorthChecking";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api";
import { inr, num } from "@/lib/format";
import { type Key, useT } from "@/lib/i18n";
import type { AuditList } from "@/lib/types";
import { Receipt } from "lucide-react";

const LIMIT = 25;
const FILTERS = ["rule", "ward", "contractor", "verdict", "method"] as const;
type F = (typeof FILTERS)[number];
const short = (n: string) => n.replace(/\s*\(synthetic\)\s*$/i, "");

/** /audit: the real list. Filters live in the URL so every view is shareable. */
export function AuditPage() {
  const t = useT();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const qs = params.toString();
  const { state, retry } = useApi<AuditList>(`/api/audit?${qs}${qs ? "&" : ""}limit=${LIMIT}`);
  const offset = Number(params.get("offset") ?? 0) || 0;

  const set = (patch: Record<string, string | null>) => {
    const q = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(patch)) {
      if (v) q.set(k, v);
      else q.delete(k);
    }
    if (!("offset" in patch)) q.delete("offset");
    router.replace(`${pathname}${q.toString() ? `?${q}` : ""}`, { scroll: false });
  };
  const data = state.status === "ready" ? state.data : null;
  const label = (f: F, v: string): string =>
    f === "rule" ? t(`rule.${v}.short` as Key)
    : f === "ward" ? `${data?.wards[v] ?? v}`.split(",")[0]
    : f === "contractor" ? short(data?.contractors[v] ?? v)
    : f === "verdict" ? (v === "none" ? t("audit.noverdict") : t(({ worth_checking: "claude.worth", likely_justified: "claude.justified", needs_more_info: "claude.more" } as Record<string, Key>)[v]))
    : v;
  const title: Record<F, Key> = { rule: "audit.f.rule", ward: "audit.f.ward", contractor: "audit.f.contractor", verdict: "audit.f.verdict", method: "audit.f.method" };
  const filtered = FILTERS.some((f) => params.get(f)) || params.get("tier") === "all";
  const csv = `/api/audit.csv?${qs}`;

  return (
    <PageShell title={t("audit.title")} subtitle={t("audit.sub")}>
      <div className="flex flex-wrap items-end gap-3">
        {FILTERS.map((f) => {
          const cur = params.get(f) ?? "";
          const facet = data?.facets[f] ?? {};
          const keys = Object.keys(facet).sort((a, b) => facet[b] - facet[a]);
          if (cur && !keys.includes(cur)) keys.unshift(cur);
          return (
            <label key={f} className="flex min-w-[10rem] flex-1 flex-col gap-1 text-[13px] font-medium text-muted-foreground sm:flex-none">
              {t(title[f])}
              <select
                value={cur}
                onChange={(e) => set({ [f]: e.target.value || null })}
                className="h-11 rounded-lg border bg-surface px-3 text-[15px] font-normal text-ink"
              >
                <option value="">{t("audit.all")}</option>
                {keys.map((k) => (
                  <option key={k} value={k}>
                    {label(f, k)} ({num(facet[k] ?? 0)})
                  </option>
                ))}
              </select>
            </label>
          );
        })}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1">
        <label className="flex min-h-11 cursor-pointer items-center gap-2 text-[15px] text-ink">
          <input
            type="checkbox"
            checked={params.get("tier") === "all"}
            onChange={(e) => set({ tier: e.target.checked ? "all" : null })}
            className="size-5 accent-[var(--accent)]"
          />
          {t("audit.includeReview")}
        </label>
        {filtered && (
          <button type="button" onClick={() => router.replace(pathname, { scroll: false })} className="min-h-11 font-medium text-primary underline underline-offset-4">
            {t("audit.reset")}
          </button>
        )}
        <a href={csv} download className={`${buttonVariants({ variant: "outline" })} ml-auto h-11 gap-2 px-4`}>
          <Download className="size-4" aria-hidden />
          {t("audit.csv")}
        </a>
      </div>

      <div className="mt-4" aria-live="polite">
        {state.status === "error" ? (
          <ErrorBox message={state.message} onRetry={retry} />
        ) : !data ? (
          <div className="space-y-2" aria-busy="true">
            {Array.from({ length: 8 }, (_, i) => (
              <Skeleton key={i} className="h-20 rounded-xl" />
            ))}
          </div>
        ) : data.items.length === 0 ? (
          <p role="status" className="rounded-2xl border bg-surface p-8 text-center text-muted-foreground">
            {t("audit.empty")}
          </p>
        ) : (
          <>
            <p className="mb-2 text-sm text-muted-foreground">
              {t("audit.total", { n: num(data.total) })} · {t("audit.range", { from: offset + 1, to: Math.min(offset + LIMIT, data.total), total: num(data.total) })}
            </p>
            <ul className="divide-y overflow-hidden rounded-2xl border bg-surface">
              {data.items.map((f) => {
                const Icon = RULE_ICON[f.rule] ?? Receipt;
                return (
                  <li key={f.flag_id}>
                    <Link href={`/flag/${f.flag_id}`} className="flex flex-wrap items-center gap-x-4 gap-y-1.5 p-3.5 hover:bg-background sm:p-4">
                      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-[var(--tone-check-bg)] text-[var(--tone-check-ink)]">
                        <Icon className="size-4.5" aria-hidden />
                      </span>
                      <span className="min-w-0 flex-1 basis-60">
                        <span className="block font-semibold text-ink">{t(`rule.${f.rule}.title` as Key)}</span>
                        <span className="block text-[13px] text-muted-foreground">
                          {f.work_order_ids[0]} · {f.ward_name.split(",")[0]} ({f.ward_code}) · {short(f.contractor_name)} · {f.repair_method}
                        </span>
                        {f.headline && <span className="mt-0.5 block text-[13px] text-ink">{f.headline}</span>}
                      </span>
                      <span className="flex items-center gap-2">
                        {f.tier === "review" && <Chip tone="neutral">{t("audit.reviewTier")}</Chip>}
                        <ClaudeVerdictChip verdict={f.verdict} />
                        {f.amount_inr > 0 && <span className="text-lg font-semibold text-ink">{inr(f.amount_inr)}</span>}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
            <div className="mt-4 flex items-center justify-between gap-3">
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => set({ offset: String(Math.max(0, offset - LIMIT)) || null })}
                className={`${buttonVariants({ variant: "outline" })} h-11 px-5`}
              >
                {t("audit.prev")}
              </button>
              <button
                type="button"
                disabled={offset + LIMIT >= data.total}
                onClick={() => set({ offset: String(offset + LIMIT) })}
                className={`${buttonVariants({ variant: "outline" })} h-11 px-5`}
              >
                {t("audit.next")}
              </button>
            </div>
          </>
        )}
      </div>
    </PageShell>
  );
}
