"use client";

import Link from "next/link";
import { LangToggle } from "@/components/LangToggle";
import { type Key, useT } from "@/lib/i18n";

const LINKS: { href: string; key: Key }[] = [
  { href: "/audit", key: "nav.audit" },
  { href: "/scorecards", key: "nav.scorecards" },
  { href: "/plan", key: "nav.next" },
  { href: "/ask", key: "nav.ask" },
];

export function TopNav() {
  const t = useT();
  return (
    <nav
      aria-label="Main"
      className="relative z-10 mx-auto flex w-full max-w-[1280px] flex-wrap items-center justify-between gap-x-4 px-4 py-2 sm:px-6 sm:py-3 print:hidden"
    >
      <Link href="/" className="order-1 flex min-h-11 items-center gap-1.5 text-lg font-semibold tracking-tight text-ink">
        <span className="text-primary" aria-hidden>
          ₹
        </span>
        RoadRupee
      </Link>
      <div className="order-2 sm:order-3">
        <LangToggle />
      </div>
      <ul className="order-3 flex w-full items-center justify-between sm:order-2 sm:ml-auto sm:w-auto sm:gap-1">
        {LINKS.map((l) => (
          <li key={l.href}>
            <Link
              href={l.href}
              className="flex min-h-11 items-center rounded-lg px-2 text-[15px] font-medium whitespace-nowrap text-ink hover:bg-surface/70 sm:px-3"
            >
              {t(l.key)}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
