"use client";

import { ArrowRight, ListChecks } from "lucide-react";
import Link from "next/link";
import { Chip } from "@/components/Chip";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api";
import { num } from "@/lib/format";
import { type Key, useT } from "@/lib/i18n";
import type { AuditStrip as Strip } from "@/lib/types";

const link = "font-semibold text-primary underline underline-offset-4";

/** Under the hook band: how the audit works, in one line, and one honest example of a flag that is probably fine. */
export function AuditStrip() {
  const t = useT();
  const { state } = useApi<Strip>("/api/home/audit-strip");
  if (state.status === "loading") return <Skeleton className="mx-auto mt-6 h-32 w-full max-w-[1280px] rounded-2xl" aria-busy="true" />;
  if (state.status === "error") return null; // decoration of the story, never a blocker
  const d = state.data;
  const ex = d.example;
  const verdicts: { v: "worth_checking" | "likely_justified" | "needs_more_info"; key: Key }[] = [
    { v: "worth_checking", key: "strip.worth" },
    { v: "likely_justified", key: "strip.justified" },
    { v: "needs_more_info", key: "strip.more" },
  ];
  return (
    <section aria-labelledby="strip-h" className="mx-auto grid w-full max-w-[1280px] gap-3 px-4 pt-6 sm:px-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
      <div className="rounded-2xl border bg-surface p-4 sm:p-5">
        <h2 id="strip-h" className="flex items-center gap-2 text-lg font-semibold tracking-tight text-ink">
          <ListChecks className="size-5 text-primary" aria-hidden />
          {t("strip.title")}
        </h2>
        <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] text-ink">
          <Link href="/audit?tier=all" className={link}>{t("strip.checked", { n: num(d.repairs_checked) })}</Link>
          <span aria-hidden>→</span>
          <Link href="/audit" className={link}>{t("strip.flagged", { n: num(d.flagged) })}</Link>
          <span aria-hidden>→</span>
          <span>{t("strip.reviewed")}</span>
        </p>
        <ul className="mt-2 flex flex-wrap gap-2">
          {verdicts.map(({ v, key }) => (
            <li key={v}>
              <Link href={`/audit?verdict=${v}`} className="inline-flex min-h-9 items-center">
                <Chip tone={v === "worth_checking" ? "check" : v === "likely_justified" ? "held" : "neutral"}>{t(key, { n: num(d[v]) })}</Chip>
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[13px] text-muted-foreground">{t("strip.note")}</p>
      </div>

      {ex && (
        <Link href={`/flag/${ex.flag_id}`} className="group flex flex-col rounded-2xl border bg-surface p-4 shadow-sm transition-shadow hover:shadow-md sm:p-5">
          <h2 className="text-lg font-semibold tracking-tight text-ink">{t("fair.title")}</h2>
          <p className="mt-2 text-[15px] leading-snug text-ink">{ex.headline}</p>
          <p className="mt-1 text-[13px] text-muted-foreground">{t("fair.sub")}</p>
          <span className="mt-auto inline-flex min-h-9 items-center gap-1 pt-2 text-sm font-semibold text-primary">
            {t("fair.see")}
            <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden />
          </span>
        </Link>
      )}
    </section>
  );
}
