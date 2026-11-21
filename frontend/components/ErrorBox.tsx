"use client";

import { useT } from "@/lib/i18n";
import { Button } from "@/components/ui/button";

export function ErrorBox({ message, onRetry }: { message: string; onRetry: () => void }) {
  const t = useT();
  return (
    <div role="alert" className="rounded-xl border bg-surface p-5">
      <p className="font-medium text-ink">{t("common.error")}</p>
      <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      <Button className="mt-3" variant="outline" onClick={onRetry}>
        {t("common.retry")}
      </Button>
    </div>
  );
}
