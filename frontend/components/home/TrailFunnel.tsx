"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useApi } from "@/lib/api";
import { num } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { TrailSummary } from "@/lib/types";

function focusTrace() {
  const el = document.getElementById("trace-input") as HTMLInputElement | null;
  if (!el) return;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" });
  el.focus({ preventScroll: true });
}

function Step({ n, label, sub, href }: { n: number; label: string; sub?: string; href?: string }) {
  const body = (
    <>
      <span className="block text-3xl leading-none font-semibold tracking-tight text-ink tabular-nums sm:text-4xl">{num(n)}</span>
      <span className="mt-1 block text-[14px] text-ink">{label}</span>
      <span className="block min-h-5 text-[13px] text-muted-foreground">{sub}</span>
    </>
  );
  return href ? (
    <Link href={href} className="block rounded-lg hover:bg-accent-soft/60">
      {body}
    </Link>
  ) : (
    <div>{body}</div>
  );
}

/** Home strip: what happened to every complaint. Steps on top, then one bar of the unique issues by outcome. */
export function TrailFunnel() {
  const t = useT();
  const { state } = useApi<TrailSummary>("/api/trail-summary");
  if (state.status !== "ready") return null; // an extra, never a blocker
  const d = state.data;
  const segs = [
    { key: "held", n: d.held, color: "var(--scale-5)", label: t("trail.held") },
    { key: "failed", n: d.failed, color: "var(--scale-1)", label: t("trail.failed"), href: "/audit" },
    { key: "open", n: d.open_or_in_progress, color: "var(--scale-2)", label: t("trail.open") },
    { key: "fwd", n: d.forwarded, color: "var(--hero-muted)", label: t("trail.fwd") },
    { key: "rej", n: d.rejected, color: "var(--border)", label: t("trail.rej") },
  ];
  return (
    <section aria-labelledby="trail-h" className="mx-auto w-full max-w-[1280px] px-4 pt-3 sm:px-6">
      <div className="rounded-2xl border bg-surface p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
          <h2 id="trail-h" className="text-lg font-semibold tracking-tight text-ink">
            {t("trail.title")}
          </h2>
          <Button type="button" variant="outline" onClick={focusTrace} className="h-11 px-4 font-semibold text-primary max-sm:w-full">
            {t("trail.cta")}
          </Button>
        </div>

        <ol className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:gap-5">
          <li><Step n={d.total} label={t("trail.total")} href="/trace" /></li>
          <li aria-hidden className="text-2xl text-muted-foreground max-sm:hidden">→</li>
          <li><Step n={d.unique} label={t("trail.unique")} sub={t("trail.merged", { n: num(d.duplicates) })} href="/trace" /></li>
          <li aria-hidden className="text-2xl text-muted-foreground max-sm:hidden">→</li>
          <li><Step n={d.linked} label={t("trail.repair")} href="/audit?tier=all" /></li>
        </ol>

        <div className="mt-4">
          <p className="mb-1.5 text-[13px] text-muted-foreground">{t("trail.barTitle", { n: num(d.unique) })}</p>
          <div role="img" aria-label={segs.map((s) => `${num(s.n)} ${s.label}`).join(", ")} className="flex h-4 w-full gap-0.5 overflow-hidden rounded-full">
            {segs.map((s) => {
              const seg = <span className="block h-full w-full" style={{ background: s.color }} />;
              return s.href ? (
                <Link key={s.key} href={s.href} title={`${num(s.n)} ${s.label}`} style={{ flexGrow: s.n, flexBasis: 0 }} className="min-w-1 hover:opacity-80">
                  {seg}
                </Link>
              ) : (
                <span key={s.key} title={`${num(s.n)} ${s.label}`} style={{ flexGrow: s.n, flexBasis: 0 }} className="min-w-1">
                  {seg}
                </span>
              );
            })}
          </div>
          <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[14px] text-ink">
            {segs.map((s) => (
              <li key={s.key} className="inline-flex items-center gap-1.5">
                <span className="size-3 rounded-[3px] border" style={{ background: s.color }} aria-hidden />
                <b className="tabular-nums">{num(s.n)}</b>
                {s.href ? (
                  <Link href={s.href} className="text-primary underline-offset-4 hover:underline">{s.label}</Link>
                ) : (
                  <span>{s.label}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
