"use client";

import { Check, Copy, Printer } from "lucide-react";
import { useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import { useT } from "@/lib/i18n";

/** The RTI draft in English or Marathi, with copy and print. Deterministic text built from the trail. */
export function RtiCard({ rti }: { rti: { en: string; mr: string } }) {
  const t = useT();
  const [lang, setLang] = useState<"en" | "mr">("en");
  const [copied, setCopied] = useState(false);
  const text = rti[lang];

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked: the text is selectable */
    }
  }
  function print() {
    document.body.dataset.print = "rti";
    window.print();
    delete document.body.dataset.print;
  }

  return (
    <section aria-labelledby="rti-h" className="rti-card rounded-2xl border bg-surface p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="rti-h" className="text-2xl font-semibold tracking-tight">
          {t("trace.rti.title")}
        </h2>
        <div role="group" aria-label={t("trace.rti.title")} className="inline-flex rounded-xl border p-0.5 print:hidden">
          {(["en", "mr"] as const).map((l) => (
            <button
              key={l}
              type="button"
              lang={l}
              aria-pressed={lang === l}
              onClick={() => setLang(l)}
              className={`min-h-10 rounded-[10px] px-4 text-sm font-semibold ${lang === l ? "bg-primary text-primary-foreground" : "text-ink hover:bg-background"}`}
            >
              {t(l === "en" ? "trace.rti.en" : "trace.rti.mr")}
            </button>
          ))}
        </div>
      </div>
      <p className="mt-1 text-sm text-muted-foreground print:hidden">{t("ev.rti.note")}</p>
      <textarea
        readOnly
        lang={lang}
        value={text}
        aria-label={t("trace.rti.title")}
        onFocus={(e) => e.currentTarget.select()}
        className="mt-3 h-[min(52svh,440px)] w-full resize-none rounded-xl border bg-background p-3 text-[14px] leading-relaxed print:h-auto print:border-0"
      />
      <div className="mt-3 flex flex-wrap gap-3 print:hidden">
        <Button type="button" onClick={copy} className="h-12 gap-2 px-5 text-base">
          {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
          {copied ? t("ev.rti.copied") : t("ev.rti.copy")}
        </Button>
        <button type="button" onClick={print} className={`${buttonVariants({ variant: "outline" })} h-12 gap-2 px-5 text-base`}>
          <Printer className="size-4" aria-hidden />
          {t("trace.rti.print")}
        </button>
      </div>
    </section>
  );
}
