"use client";

import { ChevronLeft, ChevronRight, Printer, Sparkles } from "lucide-react";
import Link from "next/link";
import { Chip } from "@/components/Chip";
import { ErrorBox } from "@/components/ErrorBox";
import { Gauge } from "@/components/Gauge";
import { TopNav } from "@/components/TopNav";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api";
import { inr, pct } from "@/lib/format";
import { type Key, useT } from "@/lib/i18n";
import type { Band, ContractorCard, Grade } from "@/lib/types";
import { wardHref } from "@/lib/wards";

const BAND_TONE: Record<Band, "held" | "neutral" | "check"> = {
  better: "held",
  as_expected: "neutral",
  worse: "check",
  neutral: "neutral",
};

function GradeCard({ g }: { g: Grade }) {
  const t = useT();
  return (
    <section aria-labelledby={`g-${g.key}`} className="flex flex-col rounded-2xl border bg-surface p-5">
      <div className="flex items-start justify-between gap-3">
        <h2 id={`g-${g.key}`} className="text-lg leading-snug font-semibold text-ink">
          {t(`grade.${g.key}.title` as Key)}
        </h2>
        <Chip tone={BAND_TONE[g.band]} className="shrink-0">
          {t(`band.${g.band}` as Key)}
        </Chip>
      </div>
      <p className="mt-3 text-3xl leading-none font-semibold tracking-tight text-ink">{g.headline}</p>
      <div className="mt-4">
        <Gauge value={g.value} benchmark={g.benchmark} min={g.scale_min} max={g.scale_max} band={g.band} label={`${g.headline}. ${g.detail}`} />
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{g.detail}</p>
    </section>
  );
}

function Body({ c }: { c: ContractorCard }) {
  const t = useT();
  return (
    <div className="space-y-6">
      <section aria-labelledby="plain-h" className="rounded-2xl border bg-surface p-5 sm:p-6">
        <h2 id="plain-h" className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <Sparkles className="size-5 text-primary" aria-hidden />
          {t("contractor.summary.title")}
        </h2>
        <p className="mt-3 max-w-3xl text-[17px] leading-relaxed text-ink">{c.summary}</p>
        {c.small_sample && (
          <div className="mt-3">
            <Chip tone="neutral">{t("contractor.few")}</Chip>
          </div>
        )}
        {c.summary_source === "template" && <p className="mt-3 text-[13px] text-muted-foreground">{t("contractor.summary.auto")}</p>}
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        {c.grades.map((g) => (
          <GradeCard key={g.key} g={g} />
        ))}
      </div>

      <section aria-labelledby="wards-h" className="rounded-2xl border bg-surface p-5 sm:p-6">
        <h2 id="wards-h" className="text-2xl font-semibold tracking-tight">
          {t("contractor.wards.title")}
        </h2>
        <ul className="mt-3 divide-y">
          {c.wards.map((w) => (
            <li key={w.ward_code}>
              <Link href={wardHref(w.ward_slug, { tab: "money" })} className="group flex min-h-14 items-center justify-between gap-3 py-2.5">
                <span>
                  <span className="font-semibold text-ink">
                    {t("picker.ward", { code: w.ward_code })} · <span className="font-normal">{w.ward_name}</span>
                  </span>
                  <span className="mt-0.5 block text-[13px] text-muted-foreground">
                    {t("contractor.ward.line", { failed: pct(w.failed_pct, 0), expected: pct(w.reopen_expected_pct, 0), n: w.work_orders })}
                    {w.small_sample && <Chip tone="neutral" className="ml-2 align-middle">{t("money.few")}</Chip>}
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-1 text-sm font-semibold text-ink">
                  {inr(w.spend_inr)}
                  <ChevronRight className="size-4 text-primary transition-transform group-hover:translate-x-0.5" aria-hidden />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <div className="flex flex-wrap items-center gap-3 print:hidden">
        <button type="button" onClick={() => window.print()} className={`${buttonVariants()} h-12 gap-2 px-5 text-base`}>
          <Printer className="size-4" aria-hidden />
          {t("contractor.print")}
        </button>
      </div>
      <p className="text-[13px] text-muted-foreground">
        {t("contractor.footer")} {t("common.synthetic")} {t("common.fairNote")}
      </p>
    </div>
  );
}

export function ContractorPage({ id }: { id: string }) {
  const t = useT();
  const { state, retry } = useApi<ContractorCard>(`/api/contractors/${encodeURIComponent(id)}`);
  const c = state.status === "ready" ? state.data : null;
  const notFound = state.status === "error" && state.message.includes("404");

  return (
    <>
      <header className="hero-sky">
        <TopNav />
        <div className="mx-auto w-full max-w-[1100px] px-4 pt-2 pb-8 sm:px-6">
          <Link href="/" className="inline-flex min-h-11 items-center gap-1 text-[15px] font-medium text-primary print:hidden">
            <ChevronLeft className="size-4" aria-hidden />
            {t("ward.back")}
          </Link>
          {notFound ? (
            <h1 className="mt-3 text-3xl font-semibold tracking-tight">{t("contractor.notFound")}</h1>
          ) : state.status === "error" ? (
            <div className="mt-3 max-w-xl">
              <ErrorBox message={state.message} onRetry={retry} />
            </div>
          ) : c ? (
            <div className="mt-1">
              <p className="text-[13px] font-semibold tracking-[0.14em] text-primary">{t("contractor.eyebrow")}</p>
              <h1 className="mt-1 text-3xl leading-tight font-semibold tracking-tight text-ink sm:text-5xl">{c.contractor_name}</h1>
              <p className="mt-2 text-[15px] text-hero-muted">
                {t("contractor.facts", { wards: c.wards_active, jobs: c.work_orders, spend: inr(c.spend_inr) })}
              </p>
            </div>
          ) : (
            <div className="mt-3" aria-busy="true">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="mt-3 h-12 w-full max-w-lg" />
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1100px] flex-1 px-4 pt-6 pb-16 sm:px-6">
        {c ? (
          <Body c={c} />
        ) : state.status === "loading" ? (
          <div className="space-y-4" aria-busy="true">
            <Skeleton className="h-40 rounded-2xl" />
            <Skeleton className="h-64 rounded-2xl" />
          </div>
        ) : null}
      </main>
    </>
  );
}
