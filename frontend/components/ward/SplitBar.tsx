/** A bar whose length is the spend (relative to the biggest row) and whose colours split held (teal) from didn't hold (red). */
export function SplitBar({
  spend,
  held,
  failed,
  max,
  label,
}: {
  spend: number;
  held: number;
  failed: number;
  max: number;
  label: string;
}) {
  const width = max ? (spend / max) * 100 : 0;
  const heldShare = spend ? (held / spend) * 100 : 0;
  return (
    <div role="img" aria-label={label} className="h-4 w-full rounded-full bg-border/60">
      <div className="flex h-full overflow-hidden rounded-full" style={{ width: `${Math.max(width, 2)}%` }}>
        <span className="h-full" style={{ width: `${heldShare}%`, background: "var(--scale-5)" }} />
        {failed > 0 && <span className="h-full flex-1" style={{ background: "var(--scale-1)" }} />}
      </div>
    </div>
  );
}
