import { Suspense } from "react";
import { TracePage } from "@/components/trace/TracePage";

export const metadata = { title: "Trace my complaint · RoadRupee" };

export default function Page() {
  return (
    <Suspense>
      <TracePage />
    </Suspense>
  );
}
