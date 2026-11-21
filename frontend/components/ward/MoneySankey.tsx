"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { ResponsiveContainer, Sankey, Tooltip } from "recharts";
import { inr } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { FlowNode, WardFlow } from "@/lib/types";

type NodeProps = {
  x: number;
  y: number;
  width: number;
  height: number;
  index: number;
  payload: FlowNode & { name: string };
  containerWidth?: number;
};

const NODE_FILL: Record<FlowNode["kind"], string> = {
  spend: "var(--ink)",
  contractor: "var(--hero-muted)",
  method: "var(--chart-rain)",
  outcome: "var(--hero-muted)", // overridden per outcome below
};

const short = (s: string) => s.replace(/\s*\(synthetic\)\s*$/i, "");

/** Money flow: ward spend, to contractors, to repair types, to held / didn't hold. Colour = outcome only. */
export function MoneySankey({ flow }: { flow: WardFlow }) {
  const t = useT();
  const router = useRouter();

  const data = useMemo(
    () => ({
      nodes: flow.nodes.map((n) => ({ ...n, name: short(n.label) })),
      links: flow.links.map((l) => ({ ...l })),
    }),
    [flow],
  );

  function Node({ x, y, width, height, payload }: NodeProps) {
    const k = payload.kind;
    const fill = k === "outcome" ? (payload.outcome === "held" ? "var(--scale-5)" : "var(--scale-1)") : NODE_FILL[k];
    const clickable = k === "contractor" && payload.contractor_id;
    const text = k === "outcome" || k === "spend" ? `${payload.name}  ${inr(payload.value_inr)}` : payload.name;
    return (
      <g
        style={{ cursor: clickable ? "pointer" : "default" }}
        onClick={clickable ? () => router.push(`/contractor/${payload.contractor_id}`) : undefined}
      >
        <rect x={x} y={y} width={width} height={Math.max(height, 2)} fill={fill} rx={2} />
        {height > 9 && (
          <text
            x={x + width + 8}
            y={y + height / 2}
            textAnchor="start"
            dominantBaseline="middle"
            fill="var(--ink)"
            stroke="var(--surface)"
            strokeWidth={3}
            strokeLinejoin="round"
            paintOrder="stroke"
            fontSize={12}
            fontWeight={k === "outcome" || k === "spend" ? 600 : 400}
          >
            {text}
          </text>
        )}
      </g>
    );
  }

  function Link(props: {
    sourceX: number;
    targetX: number;
    sourceY: number;
    targetY: number;
    sourceControlX: number;
    targetControlX: number;
    linkWidth: number;
    payload: { outcome?: "held" | "failed" | null; target: { outcome?: "held" | "failed" | null } };
  }) {
    const { sourceX, targetX, sourceY, targetY, sourceControlX, targetControlX, linkWidth, payload } = props;
    const outcome = payload.outcome ?? payload.target?.outcome ?? null;
    const stroke = outcome === "held" ? "var(--scale-5)" : outcome === "failed" ? "var(--scale-1)" : "var(--chart-rain)";
    return (
      <path
        d={`M${sourceX},${sourceY} C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}`}
        fill="none"
        stroke={stroke}
        strokeOpacity={outcome ? 0.42 : 0.22}
        strokeWidth={Math.max(linkWidth, 1)}
      />
    );
  }

  return (
    <div role="img" aria-label={t("money.flow.desc")}>
      <ResponsiveContainer width="100%" height={560}>
        <Sankey
          data={data}
          node={Node as never}
          link={Link as never}
          nodePadding={14}
          nodeWidth={10}
          sort={false}
          margin={{ top: 8, right: 170, bottom: 8, left: 8 }}
        >
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const p = payload[0].payload as { value?: number; source?: { name: string }; target?: { name: string }; name?: string };
              return (
                <div className="rounded-lg border bg-surface p-2 text-[13px] shadow-md">
                  <p className="font-semibold text-ink">
                    {p.source && p.target ? `${p.source.name} → ${p.target.name}` : p.name}
                  </p>
                  {p.value != null && <p className="text-muted-foreground">{inr(p.value)}</p>}
                </div>
              );
            }}
          />
        </Sankey>
      </ResponsiveContainer>
    </div>
  );
}
