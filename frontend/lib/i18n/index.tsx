"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore } from "react";
import { en, type Key } from "./en";
import { hi } from "./hi";
import { mr } from "./mr";

export type Lang = "en" | "hi" | "mr";
export const LANGS: { code: Lang; label: string; name: string }[] = [
  { code: "en", label: "EN", name: "English" },
  { code: "hi", label: "हिं", name: "हिन्दी" },
  { code: "mr", label: "मरा", name: "मराठी" },
];

const DICTS: Record<Lang, Partial<Record<Key, string>>> = { en, hi, mr };
const STORAGE_KEY = "roadrupee-lang";

type Vars = Record<string, string | number>;
type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (key: Key, vars?: Vars) => string };

const I18nContext = createContext<Ctx | null>(null);

export function translate(lang: Lang, key: Key, vars?: Vars): string {
  const raw = DICTS[lang][key] ?? en[key] ?? key; // missing hi/mr keys fall back to English
  return vars ? raw.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`)) : raw;
}

const listeners = new Set<() => void>();

function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
}

function getSnapshot(): Lang {
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved === "hi" || saved === "mr" ? saved : "en";
}

// The server always renders English; the saved choice is applied right after hydration.
export function I18nProvider({ children }: { children: React.ReactNode }) {
  const lang = useSyncExternalStore(subscribe, getSnapshot, () => "en" as Lang);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((l: Lang) => {
    localStorage.setItem(STORAGE_KEY, l);
    listeners.forEach((f) => f());
  }, []);

  const value = useMemo<Ctx>(
    () => ({ lang, setLang, t: (key, vars) => translate(lang, key, vars) }),
    [lang, setLang],
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): Ctx {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
  return ctx;
}

export function useT() {
  return useI18n().t;
}

export type { Key };
