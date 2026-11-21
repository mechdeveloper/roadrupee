import Link from "next/link";
import { TopNav } from "@/components/TopNav";

export function ComingSoon({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="hero-sky min-h-[100svh]">
      <TopNav />
      <main className="mx-auto w-full max-w-[720px] px-4 py-16 sm:px-6">
        <h1 className="text-4xl font-semibold tracking-tight text-ink">{title}</h1>
        <p className="mt-3 text-lg text-hero-muted">{description}</p>
        <p role="status" className="mt-6 rounded-xl border bg-surface p-4 text-ink">
          This page is being built today. Check back soon.
        </p>
        {children}
        <Link href="/" className="mt-8 inline-flex min-h-11 items-center font-medium text-primary underline">
          ← Back to the overview
        </Link>
      </main>
    </div>
  );
}
