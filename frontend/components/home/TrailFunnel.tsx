"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useApi } from "@/lib/api";
import { num } from "@/lib/format";
import { type Key, useT } from "@/lib/i18n";
import type { TrailSummary } from "@/lib/types";

const link = "font-semibold text-primary underline underline-offset-4";

function focusTrace() {
  const el = document.getElementById("trace-input") as HTMLInputElement | null;
  if (!el) return;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" });
  el.focus({ preventScroll: true });
}

/** One line under "How we audited": what happened to every complaint, from the data. */
export function TrailFunnel() {
  const t = useT();
  const { state } = useApi<TrailSummary>("/api/trail-summary");
  if (state.status !== "ready") return null; // an extra, never a blocker
  const d = state.data;
  const steps: { key: Key; n: number; href?: string; tone?: string }[] = [
    { key: "trail.total", n: d.total, href: "/trace" },
    { key: "trail.dup", n: d.duplicates },
    { key: "trail.unique", n: d.unique, href: "/trace" },
    { key: "trail.linked", n: d.linked, href: "/audit?tier=all" },
    { key: "trail.held", n: d.held, tone: "text-scale-5" },
    { key: "trail.failed", n: d.failed, href: "/audit", tone: "text-scale-1" },
    { key: "trail.open", n: d.open_or_in_progress, href: "/trace" },
    { key: "trail.fwd", n: d.forwarded },
    { key: "trail.rej", n: d.rejected },
  ];
  return (
    <section aria-labelledby="trail-h" className="mx-auto w-full max-w-[1280px] px-4 pt-3 sm:px-6">
      <div className="rounded-2xl border bg-surface px-4 py-3 sm:px-5">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <h2 id="trail-h" className="text-lg font-semibold tracking-tight text-ink">
            {t("trail.title", { n: num(d.total) })}
          </h2>
          <Button type="button" variant="outline" onClick={focusTrace} className="h-11 gap-1.5 px-4 font-semibold text-primary">
            {t("trail.cta")}
            
          </Button>
        </div>
        <ul className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] text-ink">
          {steps.map((s, i) => (
            <li key={s.key} className="inline-flex items-center gap-2">
              {i > 0 && <span aria-hidden className="text-muted-foreground">{i === 5 ? "/" : i === 4 ? "(" : "·"}</span>}
              {s.href ? (
                <Link href={s.href} className={link}>
                  <b className={s.tone}>{num(s.n)}</b> {t(s.key)}
                </Link>
              ) : (
                <span>
                  <b className={s.tone}>{num(s.n)}</b> {t(s.key)}
                </span>
              )}
              {i === 5 && <span aria-hidden className="text-muted-foreground">)</span>}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
