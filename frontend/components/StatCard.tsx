import { Card } from "@/components/ui/card";

type Props = { label: string; value: string; note: string };

export function StatCard({ label, value, note }: Props) {
  return (
    <Card className="gap-1 p-5">
      <p className="text-[13px] font-medium text-muted-foreground">{label}</p>
      <p className="text-3xl font-semibold tracking-tight text-ink">{value}</p>
      <p className="text-[13px] text-muted-foreground">{note}</p>
    </Card>
  );
}

export function StatCardSkeleton() {
  return (
    <Card className="gap-2 p-5" aria-busy="true">
      <div className="h-3 w-2/3 animate-pulse rounded bg-border" />
      <div className="h-8 w-1/2 animate-pulse rounded bg-border" />
      <div className="h-3 w-full animate-pulse rounded bg-border" />
    </Card>
  );
}
