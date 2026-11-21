"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useT } from "@/lib/i18n";

export function RtiDialog({ open, onOpenChange, text }: { open: boolean; onOpenChange: (o: boolean) => void; text: string }) {
  const t = useT();
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked: the text is selectable in the box */
    }
  }
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="gap-3 sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-xl">{t("ev.rti.title")}</DialogTitle>
          <DialogDescription>{t("ev.rti.note")}</DialogDescription>
        </DialogHeader>
        <textarea
          readOnly
          value={text}
          aria-label={t("ev.rti.title")}
          className="h-[min(50svh,420px)] w-full resize-none rounded-lg border bg-background p-3 font-mono text-[13px] leading-relaxed"
          onFocus={(e) => e.currentTarget.select()}
        />
        <Button type="button" onClick={copy} className="h-12 gap-2 text-base">
          {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
          {copied ? t("ev.rti.copied") : t("ev.rti.copy")}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
