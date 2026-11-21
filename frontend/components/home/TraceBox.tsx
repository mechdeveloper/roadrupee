"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Chip } from "@/components/Chip";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useT } from "@/lib/i18n";
import { useReducedMotion } from "@/lib/useReducedMotion";

// Real rows from the dataset: Marathi, Hinglish, English, and a complaint ID.
export const TRACE_EXAMPLES = [
  "Madanpura मध्ये पाणी साचले आहे, गाड्या अडकल्या आहेत",
  "Mulund West station road pe itna paani hai ki bus band hai",
  "Paver blocks uprooted on footpath near signal, Bandra East",
  "BMC25-000022",
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
      <p id="trace-q" className="text-lg font-semibold tracking-tight text-ink">
        {t("hero.trace.title")}
      </p>
      <div className="mt-2 flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder={TRACE_EXAMPLES[i]}
            aria-label={t("hero.trace.aria")}
            autoFocus={autoFocus}
            className="h-12 rounded-xl bg-surface pl-9 text-base"
          />
        </div>
        <Button type="submit" className="h-12 rounded-xl px-5 text-base">
          {t("hero.trace.button")}
        </Button>
      </div>
      <div className="mt-2">
        <Chip tone="held">{t("trace.chip")}</Chip>
      </div>
    </form>
  );
}
