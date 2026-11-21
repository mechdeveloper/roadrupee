"use client";

import { Search, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Chip } from "@/components/Chip";
import { ErrorBox } from "@/components/ErrorBox";
import { PageShell } from "@/components/PageShell";
import { TRACE_EXAMPLES } from "@/components/home/TraceBox";
import { RtiCard } from "@/components/trace/RtiCard";
import { TraceStepper } from "@/components/trace/TraceStepper";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { type Key, useT } from "@/lib/i18n";
import type { TraceComplaint, TraceResponse } from "@/lib/types";

type Result = { key: string; data?: TraceResponse; error?: string };
const EXAMPLES: { label: Key; text: string }[] = [
  { label: "trace.ex.mr", text: TRACE_EXAMPLES[0] },
  { label: "trace.ex.hinglish", text: TRACE_EXAMPLES[1] },
  { label: "trace.ex.id", text: "BMC25-000036" },
];

function Alternatives({ alts, onPick }: { alts: TraceComplaint[]; onPick: (id: string) => void }) {
  const t = useT();
  return (
    <section aria-labelledby="alt-h" className="rounded-2xl border bg-surface p-5 sm:p-6">
      <h2 id="alt-h" className="text-2xl font-semibold tracking-tight">
        {t("trace.confirm.title")}
      </h2>
      <ul className="mt-3 divide-y">
        {alts.map((a) => (
          <li key={a.complaint_id} className="flex flex-wrap items-center gap-3 py-3">
            <div className="min-w-0 flex-1 basis-64">
              <p className="text-[13px] text-muted-foreground">
                <span className="font-mono">{a.complaint_id}</span> · {a.locality_text} · {a.received_at.slice(0, 10)} · {t("trace.status")}: {a.status}
              </p>
              <p className="text-[15px] text-ink">“{a.text}”</p>
            </div>
            <Button type="button" variant="outline" className="h-11 px-5" onClick={() => onPick(a.complaint_id)}>
              {t("trace.confirm.pick")}
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Loading() {
  const t = useT();
  return (
    <div role="status" aria-busy="true" className="space-y-4">
      <p className="flex items-center gap-2 text-lg font-semibold text-ink">
        <Sparkles className="size-5 animate-pulse text-primary" aria-hidden />
        {t("trace.loading")}
      </p>
      <p className="text-sm text-muted-foreground">{t("trace.loading.sub")}</p>
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} className="h-24 rounded-2xl" />
      ))}
    </div>
  );
}

export function TracePage() {
  const t = useT();
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const [text, setText] = useState(q);
  const [res, setRes] = useState<Result | null>(null);

  // Run when ?q changes. Loading is derived (q set but no result for it yet), so nothing is set synchronously here.
  useEffect(() => {
    if (!q) return;
    const ctl = new AbortController();
    fetch("/api/trace", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: q }),
      signal: ctl.signal,
    })
      .then(async (r) => {
        if (!r.ok) throw new Error(`Request failed (${r.status})`);
        return (await r.json()) as TraceResponse;
      })
      .then((data) => setRes({ key: q, data }))
      .catch((e: Error) => {
        if (e.name !== "AbortError") setRes({ key: q, error: e.message });
      });
    return () => ctl.abort();
  }, [q]);

  const go = (value: string) => {
    setText(value);
    router.push(`/trace?q=${encodeURIComponent(value.trim())}`);
  };
  const loading = !!q && res?.key !== q;
  const d = res?.key === q ? res.data : undefined;
  const err = res?.key === q ? res?.error : undefined;

  return (
    <PageShell title={t("hero.trace.title")} subtitle={t("trace.page.sub")}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim()) go(text);
        }}
        className="max-w-3xl"
      >
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <Input
              value={text}
              onChange={(e) => setText(e.target.value)}
              aria-label={t("hero.trace.aria")}
              placeholder={TRACE_EXAMPLES[0]}
              className="h-14 rounded-xl bg-surface pl-10 text-base"
            />
          </div>
          <Button type="submit" className="h-14 rounded-xl px-7 text-base">
            {t("hero.trace.button")}
          </Button>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Chip tone="held">{t("trace.chip")}</Chip>
          <span className="ml-2 text-sm text-muted-foreground">{t("trace.try")}</span>
          {EXAMPLES.map((e) => (
            <button
              key={e.label}
              type="button"
              onClick={() => go(e.text)}
              className="min-h-11 rounded-full border bg-surface px-4 text-sm font-medium text-ink hover:bg-background"
            >
              {t(e.label)}
            </button>
          ))}
        </div>
      </form>

      <div className="mt-8 space-y-6" aria-live="polite">
        {loading && <Loading />}
        {err && <ErrorBox message={err} onRetry={() => router.refresh()} />}
        {d && (
          <>
            <section aria-labelledby="ans-h" className="rounded-2xl border bg-surface p-5 sm:p-6">
              <div className="flex flex-wrap items-center gap-2">
                <h2 id="ans-h" className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
                  <Sparkles className="size-5 text-primary" aria-hidden />
                  {d.outcome === "not_found" ? t("trace.notfound.title") : t("trace.answer.title")}
                </h2>
                {d.answer.source === "template" && d.outcome !== "not_found" && d.outcome !== "needs_confirmation" && (
                  <Chip tone="neutral">{t("trace.answer.auto")}</Chip>
                )}
              </div>
              <p lang={d.answer.language === "hi-en" ? "en" : d.answer.language} className="mt-3 max-w-3xl text-[18px] leading-relaxed text-ink">
                {d.answer.text}
              </p>
              <p className="mt-3 flex flex-wrap items-center gap-2 text-[13px] text-muted-foreground">
                {d.complaint && (
                  <Chip tone="neutral">
                    {d.input_kind === "id" ? t("trace.found.id") : d.match.basis === "text-match" ? t("trace.found.text") : t("trace.found.pick")}
                  </Chip>
                )}
                {d.extraction.source === "claude" && (
                  <span>
                    {t("trace.understood")}: {d.extraction.language.toUpperCase()}
                    {d.extraction.geocoded ? ` · ${d.extraction.geocoded.locality} (${d.extraction.geocoded.ward_code})` : ""} · {d.extraction.issue_type}
                  </span>
                )}
              </p>
            </section>

            {d.outcome === "needs_confirmation" && <Alternatives alts={d.match.alternatives} onPick={go} />}

            {d.steps.length > 0 && (
              <section aria-labelledby="trail-h">
                <h2 id="trail-h" className="mb-4 text-2xl font-semibold tracking-tight">
                  {t("trace.steps.title")}
                </h2>
                <TraceStepper steps={d.steps} />
              </section>
            )}

            {d.duplicates.length > 0 && (
              <section aria-labelledby="dup-h" className="rounded-2xl border bg-surface p-5">
                <h2 id="dup-h" className="text-lg font-semibold">
                  {t("trace.dups")}
                </h2>
                <ul className="mt-2 space-y-1.5 text-sm text-muted-foreground">
                  {d.duplicates.map((x) => (
                    <li key={x.complaint_id}>
                      <button type="button" onClick={() => go(x.complaint_id)} className="font-mono font-semibold text-primary underline underline-offset-4">
                        {x.complaint_id}
                      </button>{" "}
                      · {x.channel} · {x.received_at.slice(0, 10)} · “{x.text.slice(0, 80)}”
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {d.rti && <RtiCard rti={d.rti} />}
            {d.flags.length > 0 && (
              <p className="print:hidden">
                <Link href={`/flag/${d.flags[0].flag_id}`} className="font-semibold text-primary underline underline-offset-4">
                  {t("check.see")} →
                </Link>
              </p>
            )}
            <p className="text-[13px] text-muted-foreground">
              {t("common.synthetic")} {t("common.fairNote")}
            </p>
          </>
        )}
      </div>
    </PageShell>
  );
}
