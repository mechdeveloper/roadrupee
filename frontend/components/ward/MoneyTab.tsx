"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { Chip } from "@/components/Chip";
import { ErrorBox } from "@/components/ErrorBox";
import { MoneySankey } from "@/components/ward/MoneySankey";
import { SplitBar } from "@/components/ward/SplitBar";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { type Ward, useApi } from "@/lib/api";
import { inr, pct } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { useMediaQuery } from "@/lib/useMediaQuery";
import type { WardFlow } from "@/lib/types";
import { wardHref } from "@/lib/wards";

const FEW_JOBS = 10; // below this, a failed share is a rough guide, not a verdict
const short = (name: string) => name.replace(/\s*\(synthetic\)\s*$/i, "");

/** Tab a: Where did the money go? Contractor bars on every screen width; each links to its report card. */
export function MoneyTab({ ward }: { ward: Ward }) {
  const t = useT();
  const desktop = useMediaQuery("(min-width: 1024px)");
  const { state, retry } = useApi<WardFlow>(`/api/wards/${encodeURIComponent(ward.slug)}/flow`);

  if (state.status === "loading")
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-24 rounded-2xl" />
        <Skeleton className="h-80 rounded-2xl" />
      </div>
    );
  if (state.status === "error") return <ErrorBox message={state.message} onRetry={retry} />;

  const f = state.data;
  const maxC = Math.max(...f.contractors.map((c) => c.spend_inr), 1);
  const maxM = Math.max(...f.methods.map((m) => m.spend_inr), 1);

  return (
    <div className="space-y-6">
      <section aria-labelledby="money-big" className="rounded-2xl border bg-surface p-5 sm:p-6">
        <p id="money-big" className="text-5xl leading-none font-semibold tracking-tight text-ink">
          {inr(f.spend_inr)}
        </p>
        <p className="mt-3 max-w-3xl text-[18px] leading-relaxed text-ink">
          {t("money.sentence", { spend: inr(f.spend_inr), held: inr(f.held_inr), failed: inr(f.failed_inr) })}
        </p>
        <p className="mt-2 text-sm text-muted-foreground">{t("money.note")}</p>
      </section>

      {desktop && (
        <section aria-labelledby="money-flow" className="rounded-2xl border bg-surface p-5 sm:p-6">
          <h2 id="money-flow" className="text-2xl font-semibold tracking-tight">
            {t("money.flow")}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">{t("money.flow.desc")}</p>
          <div className="mt-3">
            <MoneySankey flow={f} />
          </div>
        </section>
      )}

      <section aria-labelledby="money-c" className="rounded-2xl border bg-surface p-5 sm:p-6">
        <h2 id="money-c" className="text-2xl font-semibold tracking-tight">
          {t("money.contractors")}
        </h2>
        <ul className="mt-4 space-y-2">
          {f.contractors.map((c) => (
            <li key={c.contractor_id}>
              <Link
                href={`/contractor/${c.contractor_id}`}
                className="group block rounded-xl p-3 hover:bg-background"
                aria-label={`${short(c.contractor_name)}: ${t("money.report")}`}
              >
                <span className="flex items-baseline justify-between gap-3">
                  <span className="font-semibold text-ink">{short(c.contractor_name)}</span>
                  <span className="shrink-0 text-lg font-semibold text-ink">{inr(c.spend_inr)}</span>
                </span>
                <span className="mt-1.5 block">
                  <SplitBar
                    spend={c.spend_inr}
                    held={c.held_inr}
                    failed={c.failed_inr}
                    max={maxC}
                    label={`${t("money.heldAmt", { amount: inr(c.held_inr) })}, ${t("money.failedAmt", { amount: inr(c.failed_inr), pct: pct(c.failed_pct) })}`}
                  />
                </span>
                <span className="mt-1.5 flex flex-wrap items-center justify-between gap-x-3 text-[13px] text-muted-foreground">
                  <span>
                    {t("money.heldAmt", { amount: inr(c.held_inr) })} ·{" "}
                    <span className="font-medium text-scale-1">
                      {t("money.failedAmt", { amount: inr(c.failed_inr), pct: pct(c.failed_pct, 0) })}
                    </span>{" "}
                    · {t("money.jobs", { n: c.work_orders })}
                    {c.work_orders < FEW_JOBS && (
                      <Chip tone="neutral" className="ml-2 align-middle">
                        {t("money.few")}
                      </Chip>
                    )}
                  </span>
                  <span className="inline-flex min-h-8 items-center gap-0.5 font-semibold text-primary">
                    {t("money.report")}
                    <ChevronRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[13px] text-muted-foreground">{t("common.synthetic")}</p>
      </section>

      <section aria-labelledby="money-m" className="rounded-2xl border bg-surface p-5 sm:p-6">
        <h2 id="money-m" className="text-2xl font-semibold tracking-tight">
          {t("money.methods")}
        </h2>
        <ul className="mt-4 space-y-3">
          {f.methods.map((m) => (
            <li key={m.repair_method}>
              <span className="flex items-baseline justify-between gap-3">
                <span className="font-medium text-ink">{m.repair_method}</span>
                <span className="shrink-0 font-semibold text-ink">{inr(m.spend_inr)}</span>
              </span>
              <span className="mt-1 block">
                <SplitBar
                  spend={m.spend_inr}
                  held={m.held_inr}
                  failed={m.failed_inr}
                  max={maxM}
                  label={`${m.repair_method}: ${t("money.heldAmt", { amount: inr(m.held_inr) })}, ${t("money.failedAmt", { amount: inr(m.failed_inr), pct: pct(m.failed_pct) })}`}
                />
              </span>
              <span className="mt-1 block text-[13px] text-muted-foreground">
                <span className="font-medium text-scale-1">{t("money.failedAmt", { amount: inr(m.failed_inr), pct: pct(m.failed_pct, 0) })}</span>{" "}
                · {t("money.jobs", { n: m.work_orders })}
                {m.work_orders < FEW_JOBS && (
                  <Chip tone="neutral" className="ml-2 align-middle">
                    {t("money.few")}
                  </Chip>
                )}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <Link href={wardHref(ward.slug, { tab: "check" })} className={`${buttonVariants()} h-12 px-6 text-base`}>
        {t("money.next")}
      </Link>
    </div>
  );
}
