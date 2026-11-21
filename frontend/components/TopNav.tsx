import Link from "next/link";

const LINKS = [
  { href: "/audit", label: "Audit" },
  { href: "/scorecards", label: "Scorecards" },
  { href: "/plan", label: "Next rupee" },
  { href: "/ask", label: "Ask" },
];

export function TopNav() {
  return (
    <nav
      aria-label="Main"
      className="relative z-10 mx-auto flex w-full max-w-[1280px] flex-wrap items-center justify-between gap-x-4 px-4 py-2 sm:px-6 sm:py-3"
    >
      <Link href="/" className="flex min-h-11 items-center gap-1.5 text-lg font-semibold tracking-tight text-ink">
        <span className="text-primary" aria-hidden>
          ₹
        </span>
        RoadRupee
      </Link>
      <ul className="flex w-full items-center justify-between sm:w-auto sm:gap-1">
        {LINKS.map((l) => (
          <li key={l.href}>
            <Link
              href={l.href}
              className="flex min-h-11 items-center rounded-lg px-2 text-[15px] sm:px-3 font-medium whitespace-nowrap text-ink hover:bg-surface/70"
            >
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
