import { TopNav } from "@/components/TopNav";

/** Shared frame for list pages: sky header with nav, title and subtitle, then content. */
export function PageShell({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <>
      <header className="hero-sky">
        <TopNav />
        <div className="mx-auto w-full max-w-[1280px] px-4 pt-2 pb-8 sm:px-6">
          <h1 className="text-3xl leading-tight font-semibold tracking-tight text-ink sm:text-5xl">{title}</h1>
          {subtitle && <p className="mt-2 max-w-3xl text-[16px] text-hero-muted">{subtitle}</p>}
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1280px] flex-1 px-4 pt-6 pb-16 sm:px-6">{children}</main>
    </>
  );
}
