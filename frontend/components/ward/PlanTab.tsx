"use client";

import { Check, Printer, Share2 } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { ErrorBox } from "@/components/ErrorBox";
import { RoadCard } from "@/components/ward/RoadCard";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { type Ward, useApi } from "@/lib/api";
import { inr } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { examplePlan } from "@/lib/placeholder/plan";
import type { PlanResponse } from "@/lib/types";

/** Tab d: Where should the next rupee go? Real /api/plan; labelled example data ONLY while the route returns 501. */
export function PlanTab({ ward }: { ward: Ward }) {
  const t = useT();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { state, retry } = useApi<PlanResponse>(`/api/plan?ward=${encodeURIComponent(ward.slug)}`);
  const [copied, setCopied] = useState(false);

  const isExample = state.status === "error" && state.message.includes("501");
  const plan = useMemo<PlanResponse | null>(
    () => (state.status === "ready" ? state.data : isExample ? examplePlan(ward) : null),
    [state, isExample, ward],
  );

  // Selection lives in the URL (?sel=RD1,RD2) so a shared or printed link restores the same plan.
  const selParam = params.get("sel");
  const recommended = useMemo(
    () => new Set(plan?.items.filter((i) => i.within_budget).map((i) => i.road_id) ?? []),
    [plan],
  );
  const selected = useMemo(
    () => (selParam !== null ? new Set(selParam.split(",").filter(Boolean)) : recommended),
    [selParam, recommended],
  );
  const setSelection = (next: Set<string>) => {
    const q = new URLSearchParams(params.toString());
    q.set("sel", [...next].join(","));
    router.replace(`${pathname}?${q.toString()}`, { scroll: false });
  };
  const toggle = (id: string) => {
    const next = new Set(selected);
    if (!next.delete(id)) next.add(id);
    setSelection(next);
  };

  if (state.status === "loading")
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-28 rounded-2xl" />
        <Skeleton className="h-72 rounded-2xl" />
      </div>
    );
  if (state.status === "error" && !isExample) return <ErrorBox message={state.message} onRetry={retry} />;
  if (!plan) return null;

  const chosen = plan.items.filter((i) => selected.has(i.road_id));
  const total = chosen.reduce((s, i) => s + i.estimated_cost_inr, 0);
  const left = Math.max(plan.remaining_inr, 0);
  const over = total > left;
  const fill = left > 0 ? Math.min((total / left) * 100, 100) : total > 0 ? 100 : 0;

  async function share() {
    const url = window.location.href;
    const title = t("ward.tab.next");
    try {
      if (navigator.share) {
        await navigator.share({ title, text: `${plan?.ward_name}: ${title}`, url });
        return;
      }
    } catch {
      /* user dismissed the share sheet: fall through to copy */
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked */
    }
  }

  return (
    <div>
      {isExample && (
        <p role="note" className="mb-4 rounded-xl border border-dashed bg-surface p-3 text-sm font-medium text-ink">
          {t("plan.example")}
        </p>
      )}

      <p className="hidden text-lg font-semibold print:block">
        {t("plan.printed", { ward: plan.ward_code, date: new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }) })}
      </p>
      <p className="max-w-2xl text-muted-foreground print:hidden">{t("plan.intro")}</p>

      <div className="sticky top-2 z-30 mt-4 rounded-2xl border bg-surface p-4 shadow-md print:static print:shadow-none">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <p className="text-lg font-semibold text-ink">
            {t("plan.selected", { selected: inr(total), remaining: inr(left) })}
          </p>
          <p className="text-sm text-muted-foreground">{t("plan.fundedCount", { n: chosen.length })}</p>
        </div>
        <div
          role="img"
          aria-label={t("plan.selected", { selected: inr(total), remaining: inr(left) })}
          className="mt-2 h-3 w-full overflow-hidden rounded-full bg-border"
        >
          <div
            className="h-full rounded-full transition-[width] duration-500"
            style={{ width: `${fill}%`, background: over ? "var(--scale-1)" : "var(--accent)" }}
          />
        </div>
        <p className={`mt-1 text-sm ${over ? "font-medium text-scale-1" : "text-muted-foreground"}`}>
          {left === 0
            ? t("plan.noBudget")
            : over
              ? t("plan.over", { amount: inr(total - left) })
              : t("plan.budgetLeft", { amount: inr(left - total) })}
        </p>
      </div>

      <div className="mt-3 flex flex-wrap gap-2 print:hidden">
        <button
          type="button"
          onClick={() => setSelection(recommended)}
          className={`${buttonVariants({ variant: "outline" })} h-11 px-4`}
        >
          {t("plan.recommended")}
        </button>
        <button type="button" onClick={() => setSelection(new Set())} className={`${buttonVariants({ variant: "outline" })} h-11 px-4`}>
          {t("plan.clear")}
        </button>
        <span className="flex-1" />
        <button type="button" onClick={share} className={`${buttonVariants({ variant: "outline" })} h-11 gap-2 px-4`}>
          {copied ? <Check className="size-4" aria-hidden /> : <Share2 className="size-4" aria-hidden />}
          {copied ? t("plan.copied") : t("common.share")}
        </button>
        <button type="button" onClick={() => window.print()} className={`${buttonVariants()} h-11 gap-2 px-4`}>
          <Printer className="size-4" aria-hidden />
          {t("common.print")}
        </button>
      </div>

      <details className="mt-4 print:hidden">
        <summary className="min-h-11 cursor-pointer py-2.5 font-medium text-primary">{t("plan.formula")}</summary>
        <ul className="grid gap-2 pb-2 sm:grid-cols-2">
          {plan.formula.weights.map((w) => (
            <li key={w.key} className="rounded-xl border bg-surface p-3 text-sm">
              <span className="font-semibold text-ink">
                {w.label} · {w.weight}
              </span>
              <span className="mt-0.5 block text-muted-foreground">{w.description}</span>
            </li>
          ))}
        </ul>
        <p className="text-[13px] text-muted-foreground">{plan.formula.note}</p>
      </details>

      {plan.items.length === 0 ? (
        <p role="status" className="mt-6 rounded-2xl border bg-surface p-6 text-center text-muted-foreground">
          {t("plan.empty")}
        </p>
      ) : (
        <ol className="mt-4 grid gap-4 lg:grid-cols-2">
          {plan.items.map((it) => (
            <li key={it.road_id}>
              <RoadCard item={it} selected={selected.has(it.road_id)} onToggle={() => toggle(it.road_id)} />
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
