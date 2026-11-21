"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TraceResult } from "@/components/hero/TraceResult";
import type { TraceResult as Result } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useReducedMotion } from "@/lib/useReducedMotion";

// Real rows from the dataset: Marathi, Hinglish, English, and a complaint ID.
const EXAMPLES = [
  "Madanpura मध्ये पाणी साचले आहे, गाड्या अडकल्या आहेत",
  "Mulund West station road pe itna paani hai ki bus band hai",
  "Paver blocks uprooted on footpath near signal, Bandra East",
  "BMC25-000022",
];

type Phase = "idle" | "loading" | "error";

export function HeroTrace() {
  const t = useT();
  const reduced = useReducedMotion();
  const [text, setText] = useState("");
  const [focused, setFocused] = useState(false);
  const [i, setI] = useState(0);
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    if (reduced || focused || text) return; // pause while typing / focused / reduced motion
    const id = setInterval(() => setI((n) => (n + 1) % EXAMPLES.length), 3500);
    return () => clearInterval(id);
  }, [reduced, focused, text]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setPhase("loading");
    try {
      const r = await fetch("/api/trace", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!r.ok) throw new Error(String(r.status));
      setResult((await r.json()) as Result);
      setPhase("idle");
    } catch {
      setPhase("error");
    }
  }

  return (
    <section aria-labelledby="trace-h">
      <h2 id="trace-h" className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">
        {t("hero.trace.title")}
      </h2>
      <p className="mt-1 text-[15px] text-hero-muted">
        {t("hero.trace.help")}
      </p>
      <form onSubmit={submit} className="mt-3 flex flex-col gap-3 sm:flex-row">
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={EXAMPLES[i]}
          aria-label={t("hero.trace.aria")}
          className="h-14 w-full rounded-xl sm:flex-1 bg-surface px-4 text-base"
        />
        <Button type="submit" className="h-14 rounded-xl px-8 text-base" disabled={phase === "loading"}>
          {phase === "loading" ? "…" : t("hero.trace.button")}
        </Button>
      </form>
      {phase === "idle" && result && <TraceResult r={result} />}
      {phase === "error" && (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {t("hero.trace.error")}
        </p>
      )}
    </section>
  );
}
