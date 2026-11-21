"use client";

import { Mic, Square } from "lucide-react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { type Key, useI18n } from "@/lib/i18n";

/* Minimal typing for the browser Web Speech API (not in lib.dom for all TS versions). */
type Rec = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type RecCtor = new () => Rec;

const LOCALE = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" } as const;

function ctor(): RecCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: RecCtor; webkitSpeechRecognition?: RecCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Mic inside the Trace input. Interim text streams into the input; the final transcript stays there (never auto-submits). */
export function MicButton({ onText, className = "" }: { onText: (text: string) => void; className?: string }) {
  const { lang, t } = useI18n();
  const supported = useSyncExternalStore(
    () => () => {},
    () => ctor() !== null,
    () => false, // server and hydration render: no button, so markup matches
  );
  const [listening, setListening] = useState(false);
  const [msg, setMsg] = useState<Key | null>(null);
  const rec = useRef<Rec | null>(null);

  useEffect(() => {
    return () => rec.current?.stop();
  }, []);

  if (!supported) return null;

  function toggle() {
    if (listening) {
      rec.current?.stop();
      return;
    }
    const C = ctor();
    if (!C) return;
    const r = new C();
    r.lang = LOCALE[lang];
    r.interimResults = true;
    r.continuous = false;
    setMsg(null);
    let heard = false;
    r.onresult = (e) => {
      let text = "";
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
      if (text.trim()) heard = true;
      onText(text.trim());
    };
    r.onerror = (e) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") setMsg("mic.denied");
      else if (e.error === "no-speech") setMsg("mic.nospeech");
      else if (e.error !== "aborted") setMsg("mic.error");
      heard = true; // an error message already explains the outcome
    };
    r.onend = () => {
      setListening(false);
      if (!heard) setMsg("mic.nospeech");
    };
    rec.current = r;
    try {
      r.start();
      setListening(true);
    } catch {
      setMsg("mic.error");
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={toggle}
        aria-pressed={listening}
        aria-label={t(listening ? "mic.stop" : "mic.start")}
        className={`absolute top-1/2 right-2 flex size-10 -translate-y-1/2 items-center justify-center rounded-full transition-colors ${
          listening ? "bg-[var(--tone-check-bg)] text-scale-1" : "text-muted-foreground hover:bg-accent-soft hover:text-ink"
        } ${className}`}
      >
        {listening ? <Square className="size-4 animate-pulse fill-current" aria-hidden /> : <Mic className="size-5" aria-hidden />}
        {listening && <span className="absolute inset-0 animate-ping rounded-full bg-scale-1/20 motion-reduce:hidden" aria-hidden />}
      </button>
      <span role="status" aria-live="polite" className="absolute top-full left-1 mt-1 text-[13px] whitespace-nowrap">
        {listening ? <span className="font-medium text-scale-1">{t("mic.listening")}</span> : msg ? <span className="text-muted-foreground">{t(msg)}</span> : null}
      </span>
    </>
  );
}
