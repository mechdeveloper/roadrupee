"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Chip } from "@/components/Chip";
import { Button } from "@/components/ui/button";
import { MicButton } from "@/components/trace/MicButton";
import { Input } from "@/components/ui/input";
import { type Key, useT } from "@/lib/i18n";
import { useReducedMotion } from "@/lib/useReducedMotion";

// Real rows from the dataset: Marathi, Hinglish, English, and a complaint ID.
export const TRACE_EXAMPLES = [
  "Madanpura मध्ये पाणी साचले आहे, गाड्या अडकल्या आहेत",
  "Mulund West station road pe itna paani hai ki bus band hai",
  "Paver blocks uprooted on footpath near signal, Bandra East",
  "BMC25-000022",
];

const EXAMPLE_CHIPS: { label: Key; text: string }[] = [
  { label: "trace.ex.mr", text: TRACE_EXAMPLES[0] },
  { label: "trace.ex.hinglish", text: TRACE_EXAMPLES[1] },
  { label: "trace.ex.id", text: "BMC25-000036" },
];

/** Compact "Trace my complaint" box. Submitting opens /trace and runs it there. */
export function TraceBox({ initial = "", autoFocus = false }: { initial?: string; autoFocus?: boolean }) {
  const t = useT();
  const router = useRouter();
  const reduced = useReducedMotion();
  const [text, setText] = useState(initial);
  const [focused, setFocused] = useState(false);
  const [i, setI] = useState(0);

  useEffect(() => {
    if (reduced || focused || text) return;
    const id = setInterval(() => setI((n) => (n + 1) % TRACE_EXAMPLES.length), 3500);
    return () => clearInterval(id);
  }, [reduced, focused, text]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (text.trim()) router.push(`/trace?q=${encodeURIComponent(text.trim())}`);
  }

  return (
    <form onSubmit={submit} aria-labelledby="trace-q">
      <h2 id="trace-q" className="text-3xl leading-tight font-semibold tracking-tight text-ink sm:text-4xl">
        {t("hero.trace.title")}
      </h2>
      <div className="mt-3 flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3.5 size-5 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder={TRACE_EXAMPLES[i]}
            aria-label={t("hero.trace.aria")}
            autoFocus={autoFocus}
            className="h-14 rounded-xl bg-surface pl-10 pr-12 text-base sm:text-lg"
          />
          <MicButton onText={setText} />
        </div>
        <Button type="submit" className="h-14 rounded-xl px-6 text-base sm:px-8 sm:text-lg">
          {t("hero.trace.button")}
        </Button>
      </div>
      <div className="mt-6 flex flex-wrap items-center gap-2">
        <Chip tone="held">{t("trace.chip")}</Chip>
        {EXAMPLE_CHIPS.map((e) => (
          <button
            key={e.label}
            type="button"
            onClick={() => router.push(`/trace?q=${encodeURIComponent(e.text)}`)}
            className="inline-flex min-h-9 items-center rounded-full border bg-surface px-3 text-[13px] font-medium text-ink transition-colors hover:bg-accent-soft"
          >
            {t(e.label)}
          </button>
        ))}
      </div>
    </form>
  );
}
