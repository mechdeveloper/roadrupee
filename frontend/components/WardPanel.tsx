"use client";

import { ErrorBox } from "@/components/ErrorBox";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { type Flag, type Ward, useApi } from "@/lib/api";
import { inr, num, pct } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { ruleTitle, verdict } from "@/lib/plain";
import { wardHref } from "@/lib/wards";
import { useMediaQuery } from "@/lib/useMediaQuery";

const VERDICT_STYLE = {
  better: "text-scale-5",
  "about as expected": "text-ink",
  worse: "text-scale-1",
} as const;

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="px-4">
      <h3 className="text-[13px] font-semibold tracking-wide text-muted-foreground uppercase">{title}</h3>
      <div className="mt-1.5">{children}</div>
    </section>
  );
}

function Body({ ward }: { ward: Ward }) {
  const t = useT();
  const code = encodeURIComponent(ward.ward_code);
  const { state, retry } = useApi<{ total: number; items: Flag[] }>(`/api/flags?ward=${code}&tier=audit&limit=200`);

  const over = ward.spend_inr - ward.budget_inr;
  const spentPct = ward.budget_inr ? (ward.spend_inr / ward.budget_inr) * 100 : 0;
  const v = verdict(ward);

  return (
    <>
      <SheetHeader className="pr-12">
        <SheetTitle className="text-xl">
          Ward {ward.ward_code} · {ward.ward_name}
        </SheetTitle>
        <SheetDescription>Monsoon road repairs, June to September 2025. Synthetic data.</SheetDescription>
      </SheetHeader>

      <Section title="Budget vs spent">
        <p className="text-lg font-semibold">
          {inr(ward.spend_inr)} <span className="font-normal text-muted-foreground">of {inr(ward.budget_inr)}</span>
        </p>
        <div
          role="img"
          aria-label={`${pct(spentPct, 0)} of the budget spent`}
          className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-border"
        >
          <div
            className="h-full rounded-full"
            style={{ width: `${Math.min(spentPct, 100)}%`, background: over > 0 ? "var(--scale-1)" : "var(--accent)" }}
          />
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {over > 0 ? `${inr(over)} over budget` : `${inr(-over)} left`}
        </p>
      </Section>

      <Section title="Repairs that didn't hold">
        <p className="text-lg font-semibold">
          {inr(ward.failed_spend_inr)} <span className="font-normal text-muted-foreground">({pct(ward.failed_pct)} of spend)</span>
        </p>
        <p className="mt-1 text-sm text-muted-foreground">Fixes that had to be reopened within 30 days.</p>
      </Section>

      <Section title="Compared with what we'd expect">
        <p>
          For this ward&apos;s rain and flooding, repairs held up{" "}
          <strong className={VERDICT_STYLE[v]}>{v === "better" ? "better than expected" : v === "worse" ? "worse than expected" : "about as expected"}</strong>.
        </p>
        <details className="mt-1.5 text-sm text-muted-foreground">
          <summary className="min-h-11 cursor-pointer py-2.5 font-medium text-primary">How we calculate this</summary>
          <p className="pb-2">
            {pct(ward.reopen_observed_pct)} of repairs here were reopened within 30 days. Given the repair methods
            used, the rain in the week after each repair and how flood-prone the ward is, we&apos;d expect about{" "}
            {pct(ward.reopen_expected_pct)}. We only say better or worse when the gap is too big to be chance (the
            plausible range here is {pct(ward.reopen_ci_low_pct)} to {pct(ward.reopen_ci_high_pct)}).
          </p>
        </details>
      </Section>

      <Section title="Worth checking">
        {state.status === "loading" ? (
          <div className="space-y-3" aria-busy="true">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : state.status === "error" ? (
          <ErrorBox message={state.message} onRetry={retry} />
        ) : state.data.items.length === 0 ? (
          <p className="text-muted-foreground">Nothing worth checking in this ward.</p>
        ) : (
          <>
            <ol className="space-y-3">
              {[...state.data.items]
                .sort((a, b) => b.amount_inr - a.amount_inr)
                .slice(0, 5)
                .map((f) => (
                  <li key={f.flag_id} className="rounded-lg border bg-surface p-3">
                    <p className="font-medium">{ruleTitle(f.rule)}</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">{f.reason}</p>
                    <p className="mt-1 text-[13px]">
                      Evidence: work order <span className="font-semibold">{f.work_order_ids[0]}</span>
                      {f.work_order_ids.length > 1 && <>, also {f.work_order_ids.slice(1).join(", ")}</>} · money involved{" "}
                      {inr(f.amount_inr)}
                    </p>
                  </li>
                ))}
            </ol>
            <p className="mt-2 text-sm text-muted-foreground">
              Showing the 5 largest of {num(state.data.total)}. These are worth checking, not conclusions.
            </p>
          </>
        )}
      </Section>

      <div className="mt-auto space-y-2 px-4 pb-6">
        <Link href={wardHref(ward.slug)} className={`${buttonVariants()} h-12 w-full text-base`}>
          {t("common.openWard")}
        </Link>
        <a
          href={`/api/flags.csv?ward=${code}`}
          download
          className={`${buttonVariants({ variant: "outline" })} h-11 w-full`}
        >
          Download this ward&apos;s data (CSV)
        </a>
      </div>
    </>
  );
}

export function WardPanel({ ward, onClose }: { ward: Ward | null; onClose: () => void }) {
  const desktop = useMediaQuery("(min-width: 1024px)");
  return (
    <Sheet open={ward !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent
        side={desktop ? "right" : "bottom"}
        className={desktop ? "w-full gap-5 overflow-y-auto sm:max-w-md" : "max-h-[88svh] gap-5 overflow-y-auto rounded-t-2xl"}
      >
        {ward && <Body key={ward.ward_code} ward={ward} />}
      </SheetContent>
    </Sheet>
  );
}
