import { Button } from "@/components/ui/button";

export function ErrorBox({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="rounded-xl border bg-surface p-5">
      <p className="font-medium text-ink">We couldn&apos;t load this just now.</p>
      <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      <Button className="mt-3" variant="outline" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}
