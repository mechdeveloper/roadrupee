"use client";

import { Sparkles } from "lucide-react";
import { useState } from "react";
import { Chip } from "@/components/Chip";
import { buttonVariants } from "@/components/ui/button";
import { type Key, useT } from "@/lib/i18n";
import type { ClaudeReview } from "@/lib/types";

const VERDICT: Record<ClaudeReview["verdict"], { key: Key; tone: "check" | "neutral" }> = {
  worth_checking: { key: "claude.worth", tone: "check" },
  likely_justified: { key: "claude.justified", tone: "neutral" },
  needs_more_info: { key: "claude.more", tone: "neutral" },
};

/** Claude's view. Shows the stored verdict, or lets the reader ask for one (POST /api/explain/{id}). Never alters the rule result. */
export function ClaudeCard({ flagId, initial }: { flagId: string; initial: ClaudeReview | null }) {
  const t = useT();
  const [review, setReview] = useState<ClaudeReview | null>(initial);
  const [phase, setPhase] = useState<"idle" | "loading" | "error">("idle");

  async function ask() {
    setPhase("loading");
    try {
      const r = await fetch(`/api/explain/${encodeURIComponent(flagId)}`, { method: "POST" });
      if (!r.ok) throw new Error(String(r.status));
      const data = (await r.json()) as { review: ClaudeReview };
      setReview(data.review);
      setPhase("idle");
    } catch {
      setPhase("error");
    }
  }

  return (
    <section aria-labelledby="claude-h" className="rounded-2xl border bg-surface p-5 sm:p-6">
      <h2 id="claude-h" className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
        <Sparkles className="size-5 text-primary" aria-hidden />
        {t("ev.claude.title")}
      </h2>

      {review ? (
        <div className="mt-3">
          <Chip tone={VERDICT[review.verdict].tone} icon={Sparkles}>
            {t(VERDICT[review.verdict].key)}
          </Chip>
          <p className="mt-3 text-xl leading-snug font-semibold text-ink">{review.headline}</p>
          <p className="mt-2 max-w-3xl text-[16px] leading-relaxed text-ink">{review.reasoning}</p>
          {review.context_considered.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-2">
              {review.context_considered.map((c) => (
                <li key={c}>
                  <Chip tone="neutral">{c}</Chip>
                </li>
              ))}
            </ul>
          )}
          {review.source === "template" && (
            <p className="mt-3 text-[13px] text-muted-foreground">{t("ev.claude.template")}</p>
          )}
        </div>
      ) : (
        <div className="mt-3">
          <button
            type="button"
            onClick={ask}
            disabled={phase === "loading"}
            className={`${buttonVariants()} h-12 gap-2 px-6 text-base`}
          >
            <Sparkles className="size-4" aria-hidden />
            {phase === "loading" ? t("ev.claude.asking") : t("ev.claude.ask")}
          </button>
          {phase === "error" && (
            <p role="alert" className="mt-2 text-sm text-destructive">
              {t("ev.claude.error")}
            </p>
          )}
        </div>
      )}
      <p className="mt-4 text-[13px] text-muted-foreground">{t("ev.claude.note")}</p>
    </section>
  );
}
