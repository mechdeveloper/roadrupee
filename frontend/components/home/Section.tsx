"use client";

import Link from "next/link";
import { useT } from "@/lib/i18n";

/** A dashboard section: the heading is a question, with a "See all →" link. */
export function Section({
  id,
  title,
  seeAll,
  seeAllLabel,
  children,
  className = "",
}: {
  id: string;
  title: string;
  seeAll?: string;
  seeAllLabel?: string;
  children: React.ReactNode;
  className?: string;
}) {
  const t = useT();
  return (
    <section id={id} aria-labelledby={`${id}-h`} className={`scroll-mt-4 ${className}`}>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 id={`${id}-h`} className="text-2xl font-semibold tracking-tight text-ink">
          {title}
        </h2>
        {seeAll && (
          <Link href={seeAll} className="inline-flex min-h-11 items-center font-semibold text-primary underline-offset-4 hover:underline">
            {seeAllLabel ?? t("common.seeAll")}
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}
