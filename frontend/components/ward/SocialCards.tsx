"use client";

import { ArrowRight, MessagesSquare } from "lucide-react";
import Link from "next/link";
import { Chip } from "@/components/Chip";
import { ErrorBox } from "@/components/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import { type Flag, type Ward, useApi } from "@/lib/api";
import { inr } from "@/lib/format";
import { type Key, useT } from "@/lib/i18n";
import { fmtDate } from "@/lib/wards";

/** Ward "Did the fixes hold?" tab: residents say the problem is back after a repair that was recorded as holding. */
export function SocialCards({ ward }: { ward: Ward }) {
  const t = useT();
  const code = encodeURIComponent(ward.ward_code);
  const { state, retry } = useApi<{ total: number; items: Flag[] }>(`/api/flags?ward=${code}&rule=SILENT_FAILURE&tier=review&limit=50`);

  return (
    <section aria-labelledby="social-h" className="rounded-2xl border bg-surface p-5 sm:p-6">
      <h2 id="social-h" className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
        <MessagesSquare className="size-5 text-primary" aria-hidden />
        {t("social.title")}
      </h2>
      <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{t("social.sub")}</p>
      <div className="mt-4">
        {state.status === "loading" && <Skeleton className="h-32 w-full rounded-xl" aria-busy="true" />}
        {state.status === "error" && <ErrorBox message={state.message} onRetry={retry} />}
        {state.status === "ready" &&
          (state.data.items.length === 0 ? (
            <p role="status" className="rounded-xl border border-dashed p-4 text-center text-muted-foreground">
              {t("social.empty")}
            </p>
          ) : (
            <ul className="grid gap-3 md:grid-cols-2">
              {state.data.items.map((f) => {
                const posts = f.extra?.posts ?? [];
                const p = posts[0];
                if (!p) return null;
                return (
                  <li key={f.flag_id}>
                    <Link href={`/flag/${f.flag_id}`} className="group flex h-full flex-col rounded-xl border bg-background p-4 hover:shadow-md">
                      <p lang={p.language === "hi-en" ? "en" : p.language} className="text-[16px] leading-snug text-ink">
                        “{p.text}”
                      </p>
                      <p className="mt-2 flex flex-wrap items-center gap-2">
                        <Chip tone="neutral">{t(`social.lang.${p.language}` as Key)}</Chip>
                        <span className="text-[13px] text-muted-foreground">
                          {p.source} · {fmtDate(p.posted_at)} · {p.locality}
                        </span>
                      </p>
                      <p className="mt-2 text-sm text-ink">
                        {t("social.after", { n: p.days_after_repair })} · <span className="font-mono">{f.work_order_ids[0]}</span> · {inr(f.cost_inr)}
                        {posts.length > 1 && <span className="text-muted-foreground"> · {t("social.more", { n: posts.length - 1 })}</span>}
                      </p>
                      <span className="mt-auto inline-flex min-h-9 items-center gap-1 pt-2 text-sm font-semibold text-primary">
                        {t("check.see")}
                        <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden />
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          ))}
      </div>
    </section>
  );
}
