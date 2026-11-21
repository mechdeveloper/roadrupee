import type { Flag } from "@/lib/api";
import { inr } from "@/lib/format";
import type { FlagEvidence } from "@/lib/types";
import { fmtDate } from "@/lib/wards";

/** A plain, deterministic RTI starting draft built from a flag's evidence. No LLM. The user edits before sending. */
export function buildRti(flag: Flag, ev: FlagEvidence): string {
  const ids = ev.work_order_ids.join(", ");
  const wo = ev.work_orders[0];
  const q: string[] = ["Copies of the work order, estimate, measurement book and bill(s) for the work."];

  switch (ev.rule) {
    case "OVER_RATE": {
      const rc = ev.rate_checks[0];
      if (rc)
        q.push(
          `The basis for the amount billed (${inr(rc.billed_inr)}) when the rate card gives about ${inr(rc.expected_inr)} for ${rc.repair_method}.`,
        );
      break;
    }
    case "DOUBLE_BILL":
      q.push(
        `Whether work order ${ev.work_order_ids[0]} repeats the earlier work order${ev.work_order_ids.length > 2 ? "s" : ""} ${ev.work_order_ids.slice(1).join(", ")} on the same road, and which complaint it responds to.`,
      );
      break;
    case "DLP_PAID":
      q.push(
        "Whether this road was under its Defect Liability Period at the time, and why the Corporation paid for the repair instead of the original contractor.",
      );
      break;
    case "SLA_BREACH":
      q.push(
        `The reasons the work took ${wo?.actual_hours != null ? `${Math.round(wo.actual_hours)} hours` : "longer"} against a target of ${wo?.sla_hours ?? "—"} hours, and any penalty applied.`,
      );
      break;
    case "REPEAT_FAILURE":
      q.push(
        "Inspection reports, and rectification or warranty details, for the repeated failure of the same repair on this road.",
      );
      break;
  }
  q.push("The name and designation of the officer who certified the work.");

  return [
    "(Demo draft: the data in this app is synthetic. Replace with real records before use.)",
    "",
    "To,",
    "The Public Information Officer,",
    `Municipal Corporation of Greater Mumbai, Ward ${flag.ward_code} office`,
    "",
    `Subject: Information under the Right to Information Act, 2005, about road repair work order(s) ${ids}`,
    "",
    "Sir / Madam,",
    "",
    `I request the following information about road repair work order(s) ${ids} on ${ev.road.road_name} (segment ${ev.road.segment_no}, road ${ev.road.road_id}), Ward ${flag.ward_code}${wo?.completed_at ? `, completed on ${fmtDate(wo.completed_at)}` : ""}:`,
    "",
    ...q.map((line, i) => `${i + 1}. ${line}`),
    "",
    "Why I am asking: a public review of repair spending marked this job as worth checking. This is a request for records, not an accusation.",
    "",
    "Date: ____________",
    "Name and address of applicant: ____________",
  ].join("\n");
}
