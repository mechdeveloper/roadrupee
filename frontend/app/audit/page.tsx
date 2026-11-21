import { Suspense } from "react";
import { AuditPage } from "@/components/pages/AuditPage";

export const metadata = { title: "Worth checking · RoadRupee" };

export default function Page() {
  return (
    <Suspense>
      <AuditPage />
    </Suspense>
  );
}
