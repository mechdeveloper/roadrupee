"use client";

import { useInView } from "@/lib/useInView";

/** Fade + 12px slide-up the first time it scrolls into view. Static under reduced motion (see globals.css). */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const [ref, shown] = useInView<HTMLDivElement>({ once: true, threshold: 0.15 });
  return (
    <div
      ref={ref}
      className={`reveal h-full ${className ?? ""}`}
      data-shown={shown}
      style={{ ["--delay" as string]: `${delay}ms` }}
    >
      {children}
    </div>
  );
}
