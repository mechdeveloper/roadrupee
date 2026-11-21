"use client";

import { ChevronLeft, Clock, Copy, FileText, Mail, Printer, Receipt, RotateCcw, ShieldAlert, type LucideIcon, MessagesSquare } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Chip } from "@/components/Chip";
import { ErrorBox } from "@/components/ErrorBox";
import { Gauge } from "@/components/Gauge";
import { TopNav } from "@/components/TopNav";
import { ClaudeCard } from "@/components/evidence/ClaudeCard";
import { RtiDialog } from "@/components/evidence/RtiDialog";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { type Flag, useApi } from "@/lib/api";
import { inr, num } from "@/lib/format";
import { type Key, useT } from "@/lib/i18n";
import { buildRti } from "@/lib/rti";
import type { FlagEvidence, RateCheck, WorkOrderDetail } from "@/lib/types";
import { fmtDate, wardHref, wardSlug } from "@/lib/wards";

const ICON: Record<string, LucideIcon> = {
  OVER_RATE: Receipt,
  DOUBLE_BILL: Copy,
  DLP_PAID: ShieldAlert,
  SLA_BREACH: Clock,
  SILENT_FAILURE: MessagesSquare,
  REPEAT_FAILURE: RotateCcw,
};

const avg = (o: Record<string, number>) => {
  const v = Object.values(o);
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : 0;
};

function Card({ title, children, id }: { title: string; children: React.ReactNode; id?: string }) {
  return (
    <section aria-labelledby={id} className="rounded-2xl border bg-surface p-5 sm:p-6">
      <h2 id={id} className="text-2xl font-semibold tracking-tight">
        {title}
      </h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function CtxCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border bg-background p-4">
      <h3 className="text-[13px] font-semibold tracking-wide text-muted-foreground uppercase">{title}</h3>
      <div className="mt-1.5 space-y-1.5 text-[15px] text-ink">{children}</div>
    </div>
  );
}

function RateCheckCard({ rc }: { rc: RateCheck }) {
  const t = useT();
  const max = Math.max(2.5, rc.ratio * 1.1);
  return (
    <div className="mt-4 rounded-xl border bg-background p-4">
      <h3 className="text-[13px] font-semibold tracking-wide text-muted-foreground uppercase">
        {t("ev.rate.title")} · {rc.work_order_id}
      </h3>
      <dl className="mt-2 grid grid-cols-3 gap-3 text-center">
        <div>
          <dt className="text-[13px] text-muted-foreground">{t("ev.rate.standard")}</dt>
          <dd className="text-lg font-semibold">
            {inr(rc.standard_rate_inr)}
            <span className="block text-[12px] font-normal text-muted-foreground">
              {rc.unit}
              {rc.area_sqm != null ? ` × ${num(rc.area_sqm)} sqm` : ""}
            </span>
          </dd>
        </div>
        <div>
          <dt className="text-[13px] text-muted-foreground">{t("ev.rate.expected")}</dt>
          <dd className="text-lg font-semibold">{inr(rc.expected_inr)}</dd>
        </div>
        <div>
          <dt className="text-[13px] text-muted-foreground">{t("ev.rate.billed")}</dt>
          <dd className="text-lg font-semibold text-scale-1">{inr(rc.billed_inr)}</dd>
        </div>
      </dl>
      <div className="mt-3">
        <Gauge
          value={rc.ratio}
          benchmark={1}
          min={0}
          max={max}
          band={rc.ratio > rc.threshold_x ? "worse" : "as_expected"}
          label={t("ev.rate.times", { x: rc.ratio.toFixed(1), t: rc.threshold_x })}
        />
        <p className="mt-1.5 text-sm text-muted-foreground">{t("ev.rate.times", { x: rc.ratio.toFixed(1), t: rc.threshold_x })}</p>
      </div>
    </div>
  );
}

function WoCard({ wo }: { wo: WorkOrderDetail }) {
  const t = useT();
  return (
    <li className="rounded-xl border bg-background p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-mono text-[15px] font-semibold">{wo.work_order_id}</span>
        {wo.reopened_within_30d ? (
          <Chip tone="check">{t("ev.wo.failed")}</Chip>
        ) : (
          <Chip tone="held">{t("ev.wo.held")}</Chip>
        )}
      </div>
      <p className="mt-1 text-[15px] text-ink">
        {wo.repair_method} · {wo.work_type}
      </p>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-muted-foreground">{t("ev.wo.billed")}</dt>
          <dd className="font-semibold">{inr(wo.cost_inr)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{t("ev.wo.completed")}</dt>
          <dd className="font-semibold">{fmtDate(wo.completed_at)}</dd>
        </div>
        <div className="col-span-2 sm:col-span-1">
          <dt className="text-muted-foreground">{t("ev.wo.contractor")}</dt>
          <dd>
            <Link href={`/contractor/${wo.contractor_id}`} className="font-semibold text-primary underline underline-offset-4">
              {wo.contractor_name}
            </Link>
          </dd>
        </div>
      </dl>
    </li>
  );
}

function Body({ flag, ev }: { flag: Flag; ev: FlagEvidence }) {
  const t = useT();
  const [rtiOpen, setRtiOpen] = useState(false);
  const sla = ev.rule === "SLA_BREACH" ? ev.work_orders[0] : null;
  const ctx = ev.context;
  const rain = ctx.rain;
  const mailto = () => {
    const subject = `Worth checking: ${ev.claim}`;
    const body = `${ev.claim}\n\nWork order(s): ${ev.work_order_ids.join(", ")}\nEvidence: ${window.location.href}\n\n${t("common.fairNote")}`;
    window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  };

  return (
    <div className="space-y-6">
      <Card title={t("ev.how.title")} id="how-h">
        <ol className="space-y-2.5">
          {ev.how_we_checked.map((step, i) => (
            <li key={i} className="flex gap-3">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-semibold text-primary">
                {i + 1}
              </span>
              <span className="pt-0.5 text-[16px] text-ink">{step}</span>
            </li>
          ))}
        </ol>
        {ev.rate_checks.slice(0, 2).map((rc) => (
          <RateCheckCard key={rc.work_order_id} rc={rc} />
        ))}
        {sla && sla.actual_hours != null && (
          <div className="mt-4 rounded-xl border bg-background p-4">
            <p className="text-lg font-semibold">
              {Math.round(sla.actual_hours)} h <span className="font-normal text-muted-foreground">vs a {sla.sla_hours} h target</span>
            </p>
            <div className="mt-2">
              <Gauge
                value={sla.actual_hours}
                benchmark={sla.sla_hours}
                min={0}
                max={Math.max(sla.actual_hours * 1.1, sla.sla_hours * 3)}
                band="worse"
                label={`${Math.round(sla.actual_hours)} hours against a ${sla.sla_hours} hour target`}
              />
            </div>
          </div>
        )}
      </Card>

      <Card title={t("ev.context.title")} id="ctx-h">
        <div className="grid gap-3 md:grid-cols-2">
          {rain && (
            <CtxCard title={t("ev.ctx.rain")}>
              <p>{t("ev.ctx.rainLine", { before: avg(rain.week_before_mm).toFixed(0), after: avg(rain.week_after_mm).toFixed(0) })}</p>
              {rain.max_imd_alert && rain.max_imd_alert !== "Green" && <Chip tone="neutral">IMD alert: {rain.max_imd_alert}</Chip>}
              {rain.note && <p className="text-sm text-muted-foreground">{rain.note}</p>}
            </CtxCard>
          )}
          <CtxCard title={t("ev.ctx.warranty")}>
            <p>{ctx.warranty.explanation}</p>
            <div className="flex flex-wrap gap-2">
              <Chip tone="neutral">{ctx.warranty.under_dlp === "Y" ? "Under warranty (DLP)" : "Not under warranty"}</Chip>
              {ctx.warranty.utility_trench_in_remark && <Chip tone="neutral">Utility trench in remark</Chip>}
            </div>
          </CtxCard>
          {ctx.engineer_remark && (
            <CtxCard title={t("ev.ctx.remark")}>
              <blockquote className="border-l-2 border-border pl-3 text-ink italic">“{ctx.engineer_remark}”</blockquote>
            </CtxCard>
          )}
          <CtxCard title={t("ev.ctx.complaints")}>
            <p>{t("ev.ctx.complaintsLine", { n: ctx.complaints.count, votes: ctx.complaints.total_upvotes })}</p>
            {ev.complaints.slice(0, 2).map((c) => (
              <p key={c.complaint_id} className="rounded-lg bg-surface p-2 text-sm">
                <span className="font-mono text-[12px] text-muted-foreground">{c.complaint_id} · {c.language}</span>
                <br />“{c.text}”
              </p>
            ))}
            {ev.complaints_note && <p className="text-sm text-muted-foreground">{ev.complaints_note}</p>}
          </CtxCard>
          {ctx.flood_hotspots.length > 0 && (
            <CtxCard title={t("ev.ctx.hotspots")}>
              {ctx.flood_hotspots.slice(0, 3).map((h) => (
                <p key={h.hotspot_id}>
                  {h.name} · {num(h.distance_m)} m away · floods above {h.flood_threshold_mm_per_day} mm a day
                </p>
              ))}
            </CtxCard>
          )}
          <CtxCard title={t("ev.ctx.road")}>
            <p>
              {ev.road.road_name}, segment {ev.road.segment_no} · {ev.road.road_type} · {ev.road.surface}
            </p>
            <p className="text-sm text-muted-foreground">
              Last resurfaced {fmtDate(ev.road.last_resurfaced)}
              {ev.road.congestion_index_0_10 != null ? ` · congestion ${ev.road.congestion_index_0_10}/10` : ""}
            </p>
          </CtxCard>
          {ctx.big_tides.length > 0 && (
            <CtxCard title={t("ev.ctx.tides")}>
              {ctx.big_tides.slice(0, 3).map((x) => (
                <p key={x.date}>
                  {fmtDate(x.date)} · {x.height_m} m
                </p>
              ))}
            </CtxCard>
          )}
        </div>
      </Card>

      {ev.social_posts.length > 0 && (
        <Card title={t("social.title")} id="soc-h">
          <ul className="space-y-3">
            {ev.social_posts.map((p) => (
              <li key={p.post_id} className="rounded-xl border bg-background p-4">
                <p lang={p.language === "hi-en" ? "en" : p.language} className="text-[16px] text-ink">
                  “{p.text}”
                </p>
                <p className="mt-2 flex flex-wrap items-center gap-2 text-[13px] text-muted-foreground">
                  <Chip tone="neutral">{t(`social.lang.${p.language}` as Key)}</Chip>
                  {p.source} · {fmtDate(p.posted_at)} · {p.locality} · {t("social.after", { n: p.days_after_repair })}
                </p>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[13px] text-muted-foreground">{t("social.sub")}</p>
        </Card>
      )}

      <ClaudeCard flagId={flag.flag_id} initial={ev.claude_review} />

      <Card title={t("ev.wos.title")} id="wo-h">
        <ul className="space-y-3">
          {ev.work_orders.map((wo) => (
            <WoCard key={wo.work_order_id} wo={wo} />
          ))}
        </ul>
        {ev.related_work_orders.length > 0 && (
          <>
            <h3 className="mt-5 text-lg font-semibold">{t("ev.related.title")}</h3>
            <ul className="mt-2 divide-y rounded-xl border bg-background">
              {ev.related_work_orders.map((r) => (
                <li key={r.work_order_id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 p-3 text-sm">
                  <span>
                    <span className="font-mono font-semibold">{r.work_order_id}</span> · {r.relation} · {r.repair_method}
                  </span>
                  <span className="text-muted-foreground">
                    {fmtDate(r.completed_at)} · {inr(r.cost_inr)}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>

      <Card title={t("ev.actions.title")} id="act-h">
        <div className="flex flex-wrap gap-3 print:hidden">
          <button type="button" onClick={() => setRtiOpen(true)} className={`${buttonVariants()} h-12 gap-2 px-5 text-base`}>
            <FileText className="size-4" aria-hidden />
            {t("ev.actions.rti")}
          </button>
          <button type="button" onClick={mailto} className={`${buttonVariants({ variant: "outline" })} h-12 gap-2 px-5 text-base`}>
            <Mail className="size-4" aria-hidden />
            {t("ev.actions.officer")}
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            className={`${buttonVariants({ variant: "outline" })} h-12 gap-2 px-5 text-base`}
          >
            <Printer className="size-4" aria-hidden />
            {t("ev.actions.print")}
          </button>
        </div>
        <p className="mt-3 text-[13px] text-muted-foreground">{t("common.fairNote")}</p>
      </Card>

      {ev.data_notes.length > 0 && (
        <ul className="space-y-1 text-[13px] text-muted-foreground">
          {ev.data_notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
      <RtiDialog open={rtiOpen} onOpenChange={setRtiOpen} text={buildRti(flag, ev)} />
    </div>
  );
}

export function EvidencePage({ id }: { id: string }) {
  const t = useT();
  const flag = useApi<Flag>(`/api/flags/${encodeURIComponent(id)}`);
  const ev = useApi<FlagEvidence>(`/api/flags/${encodeURIComponent(id)}/evidence`);

  const f = flag.state.status === "ready" ? flag.state.data : null;
  const e = ev.state.status === "ready" ? ev.state.data : null;
  const failed = flag.state.status === "error" ? flag.state : ev.state.status === "error" ? ev.state : null;
  const Icon = (f && ICON[f.rule]) || Receipt;

  return (
    <>
      <header className="hero-sky">
        <TopNav />
        <div className="mx-auto w-full max-w-[1100px] px-4 pt-2 pb-8 sm:px-6">
          {f && (
            <Link
              href={wardHref(wardSlug(f.ward_code), { tab: "check" })}
              className="inline-flex min-h-11 items-center gap-1 text-[15px] font-medium text-primary print:hidden"
            >
              <ChevronLeft className="size-4" aria-hidden />
              {t("ev.back")}
            </Link>
          )}
          {failed ? (
            <div className="mt-4 max-w-xl">
              {failed.message.includes("404") ? (
                <h1 className="text-3xl font-semibold tracking-tight">{t("ev.notFound")}</h1>
              ) : (
                <ErrorBox message={failed.message} onRetry={() => { flag.retry(); ev.retry(); }} />
              )}
            </div>
          ) : f && e ? (
            <div className="mt-2">
              <Chip tone="check" icon={Icon}>
                {t(`rule.${f.rule}.title` as Key)}
              </Chip>
              <h1 className="mt-3 max-w-4xl text-2xl leading-snug font-semibold tracking-tight text-ink sm:text-4xl sm:leading-tight">{e.claim}</h1>
              <div className="mt-4 flex flex-wrap items-end gap-x-6 gap-y-2">
                {f.amount_inr > 0 && (
                  <p>
                    <span className="block text-5xl leading-none font-semibold tracking-tight text-scale-1">{inr(f.amount_inr)}</span>
                    <span className="mt-1 block text-[15px] text-hero-muted">{t("check.involved")}</span>
                  </p>
                )}
                <p className="text-[15px] text-hero-muted">
                  {e.road.road_name} · {t("picker.ward", { code: f.ward_code })}
                </p>
              </div>
            </div>
          ) : (
            <div className="mt-4" aria-busy="true">
              <Skeleton className="h-6 w-40" />
              <Skeleton className="mt-3 h-24 w-full max-w-3xl" />
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1100px] flex-1 px-4 pt-6 pb-16 sm:px-6">
        {f && e ? (
          <Body flag={f} ev={e} />
        ) : failed ? null : (
          <div className="space-y-6" aria-busy="true">
            <Skeleton className="h-56 rounded-2xl" />
            <Skeleton className="h-72 rounded-2xl" />
          </div>
        )}
      </main>
    </>
  );
}
