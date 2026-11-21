"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Phase = "idle" | "loading" | "soon" | "error";

export function TraceBox() {
  const [text, setText] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");

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
      setPhase(r.status === 501 ? "soon" : r.ok ? "idle" : "error");
    } catch {
      setPhase("error");
    }
  }

  return (
    <section aria-labelledby="trace-h" className="rounded-xl border bg-surface p-5 sm:p-6">
      <h2 id="trace-h" className="text-2xl font-semibold tracking-tight">
        Trace my complaint
      </h2>
      <p className="mt-1 text-muted-foreground">
        Paste your complaint in Marathi, Hindi, Hinglish or English, or a complaint ID like
        BMC25-000123.
      </p>
      <form onSubmit={submit} className="mt-4 flex flex-col gap-3 sm:flex-row">
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Andheri station ke paas bada khadda, 2 hafte se"
          aria-label="Complaint text or ID"
          className="h-11"
        />
        <Button type="submit" className="h-11 px-6" disabled={phase === "loading"}>
          {phase === "loading" ? "Tracing…" : "Trace"}
        </Button>
      </form>
      {phase === "soon" && (
        <p role="status" className="mt-3 text-sm text-muted-foreground">
          Complaint tracing is being built today. Check back soon.
        </p>
      )}
      {phase === "error" && (
        <p role="alert" className="mt-3 text-sm text-destructive">
          Something went wrong. Please try again.
        </p>
      )}
    </section>
  );
}
