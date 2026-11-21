"use client";

import { useT } from "@/lib/i18n";

/** Labelled placeholder for a tab that is not built yet. Never fake data. */
export function TabComingSoon({ title }: { title: string }) {
  const t = useT();
  return (
    <div role="status" className="rounded-2xl border border-dashed bg-surface p-8 text-center">
      <p className="text-lg font-semibold text-ink">{title}</p>
      <p className="mt-1 text-muted-foreground">{t("tab.soon")}</p>
    </div>
  );
}
