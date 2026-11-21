"use client";

import { Download } from "lucide-react";
import { useMemo, useState } from "react";
import { ErrorBox } from "@/components/ErrorBox";
import { FlagCard } from "@/components/ward/FlagCard";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { type Flag, type Ward, useApi } from "@/lib/api";
import { num } from "@/lib/format";
import { type Key, useT } from "@/lib/i18n";

const RULES = ["OVER_RATE", "DOUBLE_BILL", "DLP_PAID", "SLA_BREACH", "REPEAT_FAILURE"] as const;
const PAGE = 12;

/** Tab c: What's worth checking? Flag cards, filter by type, audit tier first. */
export function ChecksTab({ ward }: { ward: Ward }) {
  const t = useT();
  const code = encodeURIComponent(ward.ward_code);
  const { state, retry } = useApi<{ total: number; items: Flag[] }>(`/api/flags?ward=${code}&limit=1000`);
  const [rule, setRule] = useState<string>("ALL");
  const [showReview, setShowReview] = useState(false);
  const [visible, setVisible] = useState(PAGE);

  const items = useMemo(() => (state.status === "ready" ? state.data.items : []), [state]);
  const reviewCount = useMemo(() => items.filter((f) => f.tier === "review").length, [items]);

  const shown = useMemo(() => {
    return items
      .filter((f) => (showReview ? true : f.tier === "audit"))
      .filter((f) => rule === "ALL" || f.rule === rule)
      .sort((a, b) => (a.tier === b.tier ? b.amount_inr - a.amount_inr : a.tier === "audit" ? -1 : 1));
  }, [items, rule, showReview]);

  const countFor = (r: string) =>
    items.filter((f) => (showReview ? true : f.tier === "audit") && (r === "ALL" || f.rule === r)).length;

  return (
    <div>
      <p className="max-w-2xl text-muted-foreground">{t("check.intro")}</p>

      {state.status === "loading" && (
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-56 rounded-2xl" />
          ))}
        </div>
      )}
      {state.status === "error" && (
        <div className="mt-5">
          <ErrorBox message={state.message} onRetry={retry} />
        </div>
      )}

      {state.status === "ready" && (
        <>
          <div role="group" aria-label="Filter by type" className="mt-5 flex flex-wrap gap-2">
            {["ALL", ...RULES].map((r) => {
              const n = countFor(r);
              const active = rule === r;
              if (r !== "ALL" && n === 0 && !active) return null;
              return (
                <button
                  key={r}
                  type="button"
                  aria-pressed={active}
                  onClick={() => {
                    setRule(r);
                    setVisible(PAGE);
                  }}
                  className={`min-h-11 rounded-full border px-4 text-sm font-medium transition-colors ${
                    active ? "border-primary bg-primary text-primary-foreground" : "bg-surface text-ink hover:bg-background"
                  }`}
                >
                  {r === "ALL" ? t("check.filter.all") : t(`rule.${r}.short` as Key)} · {num(n)}
                </button>
              );
            })}
          </div>

          {reviewCount > 0 && (
            <button
              type="button"
              onClick={() => {
                setShowReview((v) => !v);
                setVisible(PAGE);
              }}
              className="mt-3 inline-flex min-h-11 items-center font-medium text-primary underline underline-offset-4"
            >
              {showReview ? t("check.hideReview") : t("check.showReview", { n: num(reviewCount) })}
            </button>
          )}

          {shown.length === 0 ? (
            <p role="status" className="mt-6 rounded-2xl border bg-surface p-6 text-center text-muted-foreground">
              {t("check.empty")}
            </p>
          ) : (
            <>
              <ul className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {shown.slice(0, visible).map((f) => (
                  <li key={f.flag_id}>
                    <FlagCard flag={f} />
                  </li>
                ))}
              </ul>
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <span className="text-sm text-muted-foreground">
                  {t("check.count", { shown: Math.min(visible, shown.length), total: shown.length })}
                </span>
                {visible < shown.length && (
                  <button
                    type="button"
                    onClick={() => setVisible((v) => v + PAGE)}
                    className={`${buttonVariants({ variant: "outline" })} h-11 px-5`}
                  >
                    {t("check.more")}
                  </button>
                )}
              </div>
            </>
          )}

          <div className="mt-8 border-t pt-5">
            <a
              href={`/api/flags.csv?ward=${code}`}
              download
              className={`${buttonVariants({ variant: "outline" })} h-12 gap-2 px-5 text-base`}
            >
              <Download className="size-4" aria-hidden />
              {t("common.csv")}
            </a>
            <p className="mt-2 text-[13px] text-muted-foreground">{t("common.fairNote")}</p>
          </div>
        </>
      )}
    </div>
  );
}
