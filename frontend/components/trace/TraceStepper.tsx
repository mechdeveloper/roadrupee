"use client";

import { CircleCheck, Clock, Minus, TriangleAlert, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { TraceStep } from "@/lib/types";

const ICON: Record<TraceStep["status"], { Icon: LucideIcon; ring: string; text: string }> = {
  done: { Icon: CircleCheck, ring: "bg-[var(--tone-held-bg)]", text: "text-[var(--tone-held-ink)]" },
  failed: { Icon: TriangleAlert, ring: "bg-[var(--tone-check-bg)]", text: "text-[var(--tone-check-ink)]" },
  pending: { Icon: Clock, ring: "bg-[var(--tone-neutral-bg)]", text: "text-[var(--tone-neutral-ink)]" },
  skipped: { Icon: Minus, ring: "bg-[var(--tone-neutral-bg)]", text: "text-[var(--tone-neutral-ink)]" },
};

/** Vertical trail: Complaint, issue, work order, held 30 days, warranty, action. Each step eases in. */
export function TraceStepper({ steps }: { steps: TraceStep[] }) {
  return (
    <ol className="relative">
      {steps.map((s, i) => {
        const { Icon, ring, text } = ICON[s.status];
        const last = i === steps.length - 1;
        return (
          <li key={s.key} className="step-in relative flex gap-4 pb-6 last:pb-0" style={{ ["--delay" as string]: `${i * 140}ms` }}>
            {!last && <span aria-hidden className="absolute top-11 bottom-0 left-[19px] w-0.5 bg-border" />}
            <span className={`relative z-10 flex size-10 shrink-0 items-center justify-center rounded-full ${ring} ${text}`}>
              <Icon className="size-5" aria-hidden />
            </span>
            <div className={`min-w-0 flex-1 rounded-2xl border bg-surface p-4 ${s.status === "skipped" ? "opacity-70" : ""}`}>
              <p className="text-[13px] font-semibold tracking-wide text-muted-foreground uppercase">{s.title}</p>
              <p className="mt-0.5 text-[17px] leading-snug font-semibold text-ink">{s.headline}</p>
              <p className="mt-1 text-[15px] text-ink/80">{s.detail}</p>
              {s.links.length > 0 && (
                <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                  {s.links.map((l) => (
                    <Link key={l.href} href={l.href} className="inline-flex min-h-9 items-center font-semibold text-primary underline underline-offset-4">
                      {l.label}
                    </Link>
                  ))}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
