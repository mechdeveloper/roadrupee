/** Sticky bottom bar for the screen's main actions (every screen ends with an action). Hidden when printing. */
export function ActionBar({ children }: { children: React.ReactNode }) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-40 border-t bg-surface/95 p-3 backdrop-blur print:hidden">
      <div className="mx-auto flex w-full max-w-[1100px] flex-wrap items-center justify-end gap-2 px-1 sm:px-3">{children}</div>
    </div>
  );
}
