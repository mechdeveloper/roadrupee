import type { LucideIcon } from "lucide-react";
import { ArrowRight } from "lucide-react";
import Link from "next/link";

type Props = {
  icon: LucideIcon;
  title: string;
  description: string;
  cta: string;
  href?: string;
  onClick?: () => void;
};

/** One big, friendly door into the app. Link when it navigates, button when it opens something. */
export function EntryCard({ icon: Icon, title, description, cta, href, onClick }: Props) {
  const body = (
    <>
      <span className="flex size-12 items-center justify-center rounded-xl bg-accent text-primary">
        <Icon className="size-6" aria-hidden />
      </span>
      <span className="mt-4 block text-xl font-semibold tracking-tight text-ink">{title}</span>
      <span className="mt-1 block text-[15px] text-muted-foreground">{description}</span>
      <span className="mt-4 inline-flex min-h-11 items-center gap-1.5 font-semibold text-primary">
        {cta}
        <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
      </span>
    </>
  );
  const cls =
    "group block w-full rounded-2xl border bg-surface p-5 text-left shadow-sm transition-shadow hover:shadow-md sm:p-6";
  return href ? (
    <Link href={href} className={cls}>
      {body}
    </Link>
  ) : (
    <button type="button" onClick={onClick} className={cls}>
      {body}
    </button>
  );
}
