import type { LucideIcon } from "lucide-react";

/** Tone = meaning. check = red/amber (didn't hold / worth checking), held = teal (held / fine),
 *  neutral = grey (no data / context). Never decoration. */
export type Tone = "check" | "held" | "neutral";

const TONE: Record<Tone, string> = {
  check: "bg-[var(--tone-check-bg)] text-[var(--tone-check-ink)]",
  held: "bg-[var(--tone-held-bg)] text-[var(--tone-held-ink)]",
  neutral: "bg-[var(--tone-neutral-bg)] text-[var(--tone-neutral-ink)]",
};

export function Chip({
  tone,
  icon: Icon,
  children,
  wrap = false,
  className = "",
}: {
  tone: Tone;
  icon?: LucideIcon;
  children: React.ReactNode;
  /** allow long text (e.g. a school name) to wrap instead of overflowing */
  wrap?: boolean;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex min-h-7 max-w-full items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[13px] font-medium ${wrap ? "" : "whitespace-nowrap"} ${TONE[tone]} ${className}`}
    >
      {Icon && <Icon className="size-3.5 shrink-0" aria-hidden />}
      {children}
    </span>
  );
}
