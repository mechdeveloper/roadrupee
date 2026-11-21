"use client";

import { LANGS, useI18n } from "@/lib/i18n";

export function LangToggle() {
  const { lang, setLang, t } = useI18n();
  return (
    <div role="group" aria-label={t("nav.language")} className="inline-flex rounded-xl border bg-surface/80 p-0.5">
      {LANGS.map((l) => (
        <button
          key={l.code}
          type="button"
          lang={l.code}
          title={l.name}
          aria-pressed={lang === l.code}
          onClick={() => setLang(l.code)}
          className={`min-h-10 min-w-11 rounded-[10px] px-2.5 text-sm font-semibold transition-colors ${
            lang === l.code ? "bg-primary text-primary-foreground" : "text-ink hover:bg-background"
          }`}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
