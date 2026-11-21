import type { TraceResult as Result, TraceStep } from "@/lib/api";
import { inr } from "@/lib/format";
import { useT } from "@/lib/i18n";

const DOT: Record<TraceStep["status"], string> = {
  info: "bg-border",
  ok: "bg-scale-5",
  warn: "bg-scale-2",
  bad: "bg-scale-1",
};

/** The complaint trail: one plain sentence, then the steps that prove it. */
export function TraceResult({ r }: { r: Result }) {
  const t = useT();
  return (
    <div className="mt-4 rounded-xl border bg-surface p-4 sm:p-5" role="status">
      <p className="text-base font-medium text-ink">{r.claude_summary || r.summary}</p>
      {r.claude_summary && (
        <p className="mt-1 text-[13px] text-muted-foreground">{t("trace.byClaude")} {r.summary}</p>
      )}
      {r.steps.length > 0 && (
        <ol className="mt-4 space-y-3 border-l pl-5">
          {r.steps.map((st, i) => (
            <li key={i} className="relative">
              <span className={`absolute top-1.5 -left-[25px] size-2.5 rounded-full ${DOT[st.status]}`} aria-hidden />
              <p className="text-[13px] font-medium text-muted-foreground">{st.label}</p>
              <p className="text-sm text-ink">{st.detail}</p>
            </li>
          ))}
        </ol>
      )}
      {r.history && r.history.length > 1 && (
        <div className="mt-4 overflow-x-auto">
          <p className="mb-2 text-[13px] font-medium text-muted-foreground">{t("trace.history")}</p>
          <table className="w-full text-left text-sm">
            <tbody>
              {r.history.map((h) => (
                <tr key={h.work_order_id} className="border-b last:border-0">
                  <td className="py-2 pr-3 tabular-nums">{h.completed_at}</td>
                  <td className="py-2 pr-3">{h.work_order_id}</td>
                  <td className="py-2 pr-3">{h.contractor_name.replace(" (synthetic)", "")}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{inr(h.cost_inr)}</td>
                  <td className="py-2">{h.held_up ? t("trace.heldUp") : t("trace.failed")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
