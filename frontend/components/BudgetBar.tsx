"use client";

import { inr, pct } from "@/lib/format";
import { useT } from "@/lib/i18n";

/** Spent vs budget. Turns red (worth checking) only when the ward has spent more than its budget. */
export function BudgetBar({ spent, budget, showText = true }: { spent: number; budget: number; showText?: boolean }) {
  const t = useT();
  const over = spent - budget;
  const share = budget ? (spent / budget) * 100 : 0;
  return (
    <div>
      {showText && (
        <p className="text-lg font-semibold text-ink">
          {t("ward.spentOf", { spent: inr(spent), budget: inr(budget) })}
        </p>
      )}
      <div
        role="img"
        aria-label={`${pct(share, 0)} of the budget spent`}
        className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-border"
      >
        <div
          className="h-full rounded-full transition-[width] duration-700"
          style={{ width: `${Math.min(share, 100)}%`, background: over > 0 ? "var(--scale-1)" : "var(--accent)" }}
        />
      </div>
      {showText && (
        <p className="mt-1 text-sm text-muted-foreground">
          {over > 0 ? t("ward.over", { amount: inr(over) }) : t("ward.left", { amount: inr(-over) })}
        </p>
      )}
    </div>
  );
}
