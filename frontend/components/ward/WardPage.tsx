"use client";

import { useState } from "react";
import { ChevronLeft, CloudRain, Download, Printer, Route, Search, Sparkles, Wallet, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { BudgetBar } from "@/components/BudgetBar";
import { ActionBar } from "@/components/ActionBar";
import { Chip } from "@/components/Chip";
import { ErrorBox } from "@/components/ErrorBox";
import { TopNav } from "@/components/TopNav";
import { VerdictChip } from "@/components/VerdictChip";
import { ChecksTab } from "@/components/ward/ChecksTab";
import { HeldTab } from "@/components/ward/HeldTab";
import { PlanTab } from "@/components/ward/PlanTab";
import { TabComingSoon } from "@/components/ward/TabComingSoon";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { type Ward, useApi } from "@/lib/api";
import { inr, pct } from "@/lib/format";
import { type Key, useI18n } from "@/lib/i18n";

export type TabKey = "money" | "held" | "check" | "next";
const TABS: { key: TabKey; label: Key; icon: LucideIcon }[] = [
  { key: "money", label: "ward.tab.money", icon: Wallet },
  { key: "held", label: "ward.tab.held", icon: CloudRain },
  { key: "check", label: "ward.tab.check", icon: Search },
  { key: "next", label: "ward.tab.next", icon: Route },
];
// Flip to "money" once tab a is built (money is the natural first question).
const DEFAULT_TAB: TabKey = "check";

function isTab(v: string | null): v is TabKey {
  return TABS.some((t) => t.key === v);
}

function AiSummary({ ward }: { ward: Ward }) {
  const { lang, t } = useI18n();
  const [open, setOpen] = useState(false);
  const s = ward.ai_summary;
  if (!s) return null; // hidden until the summary has been precomputed
  const text = s[lang] || s.en;
  if (!text) return null;
  return (
    <section aria-label={t("ward.summary.title")} className="rounded-2xl border bg-surface p-5">
      <p className="flex items-center gap-2 text-[13px] font-semibold tracking-wide text-primary uppercase">
        <Sparkles className="size-4" aria-hidden />
        {t("ward.summary.title")}
      </p>
      <p lang={lang} className={`mt-2 max-w-3xl text-[17px] leading-relaxed text-ink sm:line-clamp-none ${open ? "" : "line-clamp-4"}`}>
        {text}
      </p>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="min-h-11 font-medium text-primary underline underline-offset-4 sm:hidden"
      >
        {open ? t("common.less") : t("common.more")}
      </button>
    </section>
  );
}

export function WardPage({ slug }: { slug: string }) {
  const { t } = useI18n();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { state, retry } = useApi<Ward>(`/api/wards/${encodeURIComponent(slug)}`);

  const tabParam = params.get("tab");
  const tab: TabKey = isTab(tabParam) ? tabParam : DEFAULT_TAB;
  const officer = params.get("mode") === "officer";

  const setTab = (next: TabKey) => {
    const q = new URLSearchParams(params.toString());
    q.set("tab", next);
    router.replace(`${pathname}?${q.toString()}`, { scroll: false });
  };

  if (state.status === "error") {
    const notFound = state.message.includes("404");
    return (
      <div className="hero-sky min-h-[100svh]">
        <TopNav />
        <main className="mx-auto max-w-[720px] px-4 py-16 sm:px-6">
          {notFound ? (
            <>
              <h1 className="text-3xl font-semibold tracking-tight">{t("ward.notFound")}</h1>
              <p className="mt-2 text-hero-muted">{t("ward.notFound.hint")}</p>
              <Link href="/" className={`${buttonVariants()} mt-6 h-12 px-6 text-base`}>
                {t("ward.back")}
              </Link>
            </>
          ) : (
            <ErrorBox message={state.message} onRetry={retry} />
          )}
        </main>
      </div>
    );
  }

  const ward = state.status === "ready" ? state.data : null;

  return (
    <>
      <header className="hero-sky">
        <TopNav />
        <div className="mx-auto w-full max-w-[1100px] px-4 pt-2 pb-8 sm:px-6">
          <Link href="/" className="inline-flex min-h-11 items-center gap-1 text-[15px] font-medium text-primary print:hidden">
            <ChevronLeft className="size-4" aria-hidden />
            {t("ward.back")}
          </Link>

          {ward ? (
            <>
              <div className="mt-1 flex flex-wrap items-center gap-3">
                <p className="text-[13px] font-semibold tracking-[0.14em] text-primary">
                  {t("picker.ward", { code: ward.ward_code }).toUpperCase()}
                </p>
                {officer && <Chip tone="neutral">{t("ward.officer.badge")}</Chip>}
              </div>
              <h1 className="mt-1 text-3xl leading-tight font-semibold tracking-tight text-ink sm:text-5xl">
                {ward.ward_name}
              </h1>
              <p className="mt-1 text-[15px] text-hero-muted">{ward.localities.join(" · ")}</p>

              <div className="mt-6 grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border bg-surface p-5">
                  <p className="text-[13px] font-semibold tracking-wide text-muted-foreground uppercase">
                    {t("ward.budget")}
                  </p>
                  <div className="mt-1.5">
                    <BudgetBar spent={ward.spend_inr} budget={ward.budget_inr} />
                  </div>
                </div>
                <div className="rounded-2xl border bg-surface p-5">
                  <button
                    type="button"
                    onClick={() => setTab("held")}
                    className="block text-left text-4xl leading-none font-semibold tracking-tight text-scale-1 underline decoration-dotted decoration-2 underline-offset-8"
                  >
                    {inr(ward.failed_spend_inr)}
                  </button>
                  <p className="mt-2 text-[15px] text-ink">{t("ward.didnthold.sub", { pct: pct(ward.failed_pct) })}</p>
                  <VerdictChip ward={ward} className="mt-3" />
                </div>
              </div>
            </>
          ) : (
            <div className="mt-3" aria-busy="true">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="mt-3 h-12 w-full max-w-lg" />
              <div className="mt-6 grid gap-4 md:grid-cols-2">
                <Skeleton className="h-32 rounded-2xl" />
                <Skeleton className="h-32 rounded-2xl" />
              </div>
            </div>
          )}
        </div>
      </header>

      <main className={`mx-auto w-full max-w-[1100px] flex-1 px-4 pt-6 sm:px-6 ${officer ? "pb-28" : "pb-16"}`}>
        {ward && <AiSummary ward={ward} />}

        <div role="tablist" aria-label={ward?.ward_name ?? "Ward"} className="mt-6 grid grid-cols-2 gap-2 lg:grid-cols-4 print:hidden">
          {TABS.map(({ key, label, icon: Icon }) => {
            const active = tab === key;
            return (
              <button
                key={key}
                role="tab"
                id={`tab-${key}`}
                aria-selected={active}
                aria-controls={`panel-${key}`}
                type="button"
                onClick={() => setTab(key)}
                className={`flex min-h-16 items-center gap-2.5 rounded-2xl border px-3.5 py-2 text-left text-[15px] leading-snug font-semibold transition-colors ${
                  active ? "border-primary bg-primary text-primary-foreground" : "bg-surface text-ink hover:bg-background"
                }`}
              >
                <Icon className="size-5 shrink-0" aria-hidden />
                {t(label)}
              </button>
            );
          })}
        </div>

        <section role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="mt-6">
          {!ward ? (
            <Skeleton className="h-64 w-full rounded-2xl" />
          ) : tab === "check" ? (
            <ChecksTab ward={ward} />
          ) : tab === "next" ? (
            <PlanTab ward={ward} />
          ) : tab === "held" ? (
            <HeldTab ward={ward} />
          ) : (
            <TabComingSoon title={t(TABS.find((x) => x.key === tab)!.label)} />
          )}
        </section>
      </main>

      {officer && ward && (
        <ActionBar>
          <a
            href={`/api/flags.csv?ward=${encodeURIComponent(ward.ward_code)}`}
            download
            className={`${buttonVariants({ variant: "outline" })} h-12 gap-2 px-5 text-base`}
          >
            <Download className="size-4" aria-hidden />
            {t("common.csv")}
          </a>
          <button
            type="button"
            onClick={() => window.print()}
            className={`${buttonVariants()} h-12 gap-2 px-5 text-base`}
          >
            <Printer className="size-4" aria-hidden />
            {t("common.print")}
          </button>
        </ActionBar>
      )}
    </>
  );
}
