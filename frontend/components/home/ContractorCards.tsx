"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { Chip } from "@/components/Chip";
import { ErrorBox } from "@/components/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api";
import { inr } from "@/lib/format";
import { type Key, useT } from "@/lib/i18n";
import type { Band, HomeContractor } from "@/lib/types";

const TONE: Record<Band, "held" | "neutral" | "watch" | "check"> = { better: "held", as_expected: "neutral", watch: "watch", worse: "check", neutral: "neutral" };
const ROWS: { key: "speed" | "durability" | "cost"; label: Key }[] = [
  { key: "speed", label: "card.onTime" },
  { key: "durability", label: "card.lasted" },
  { key: "cost", label: "card.billed" },
];
const short = (n: string) => n.replace(/\s*\(synthetic\)\s*$/i, "");

function Card({ c }: { c: HomeContractor }) {
  const t = useT();
  const grade = (k: string) => c.grades.find((g) => g.key === k)!;
  return (
    <Link href={`/contractor/${c.contractor_id}`} className="group flex h-full flex-col rounded-2xl border bg-surface p-4 shadow-sm transition-shadow hover:shadow-md">
      <span className="flex items-start justify-between gap-2">
        <span className="text-[17px] leading-snug font-semibold text-ink">{short(c.contractor_name)}</span>
        <ChevronRight className="mt-0.5 size-4 shrink-0 text-primary transition-transform group-hover:translate-x-0.5" aria-hidden />
      </span>
      <span className="mt-0.5 text-[13px] text-muted-foreground">
        {t("card.jobs", { n: c.work_orders })} · {inr(c.spend_inr)}
      </span>
      <ul className="mt-3 space-y-2">
        {ROWS.map((r) => {
          const g = grade(r.key);
          return (
            <li key={r.key} className="flex items-center justify-between gap-2 text-[13px]">
              <span className="text-muted-foreground">{t(r.label)}</span>
              <Chip tone={TONE[g.band]}>{g.headline}</Chip>
            </li>
          );
        })}
      </ul>
      {c.small_sample && (
        <span className="mt-3">
          <Chip tone="neutral">{t("contractor.few")}</Chip>
        </span>
      )}
    </Link>
  );
}

export function ContractorCards() {
  const { state, retry } = useApi<HomeContractor[]>("/api/home/contractors");
  if (state.status === "error") return <ErrorBox message={state.message} onRetry={retry} />;
  if (state.status === "loading")
    return (
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-busy="true">
        {Array.from({ length: 8 }, (_, i) => (
          <Skeleton key={i} className="h-44 rounded-2xl" />
        ))}
      </div>
    );
  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {state.data.map((c) => (
        <li key={c.contractor_id}>
          <Card c={c} />
        </li>
      ))}
    </ul>
  );
}
