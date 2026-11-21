"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { Ward } from "@/lib/api";
import { useApi } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { Locality } from "@/lib/types";
import { searchWards, wardHref } from "@/lib/wards";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  wards: Ward[];
  /** explore = citizen browsing; officer = opens the ward page in officer mode */
  mode: "explore" | "officer";
};

function Body({ wards, mode, onDone }: { wards: Ward[]; mode: Props["mode"]; onDone: () => void }) {
  const t = useT();
  const router = useRouter();
  const [q, setQ] = useState("");
  const { state } = useApi<Locality[]>("/api/localities");
  const hits = useMemo(
    () => searchWards(q, wards, state.status === "ready" ? state.data : []),
    [q, wards, state],
  );
  const list = q.trim()
    ? hits.map((h) => ({ ward: h.ward, via: h.via }))
    : [...wards].sort((a, b) => a.ward_code.localeCompare(b.ward_code)).map((ward) => ({ ward, via: null }));

  const go = (w: Ward) => {
    onDone();
    router.push(wardHref(w.slug, mode === "officer" ? { mode: "officer" } : undefined));
  };

  return (
    <>
      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("picker.placeholder")}
          aria-label={t("picker.placeholder")}
          className="h-12 pl-10 text-base"
        />
      </div>
      <p className="text-[13px] text-muted-foreground">{t("picker.hint")}</p>
      {list.length === 0 ? (
        <p role="status" className="py-6 text-center text-muted-foreground">
          {t("picker.empty")}
        </p>
      ) : (
        <ul className="-mx-1 max-h-[50svh] overflow-y-auto">
          {list.map(({ ward, via }) => (
            <li key={ward.ward_code}>
              <button
                type="button"
                onClick={() => go(ward)}
                className="flex min-h-14 w-full flex-col items-start justify-center rounded-lg px-3 py-2 text-left hover:bg-background"
              >
                <span className="font-semibold text-ink">
                  {t("picker.ward", { code: ward.ward_code })} · <span className="font-normal">{ward.ward_name}</span>
                </span>
                {via && <span className="text-[13px] text-muted-foreground">{via}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export function WardPicker({ open, onOpenChange, wards, mode }: Props) {
  const t = useT();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="gap-3 sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-xl">{t(mode === "officer" ? "picker.title.officer" : "picker.title.explore")}</DialogTitle>
          <DialogDescription className="sr-only">{t("picker.hint")}</DialogDescription>
        </DialogHeader>
        {open && <Body wards={wards} mode={mode} onDone={() => onOpenChange(false)} />}
      </DialogContent>
    </Dialog>
  );
}
