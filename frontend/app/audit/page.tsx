import { ComingSoon } from "@/components/ComingSoon";
import { buttonVariants } from "@/components/ui/button";

export const metadata = { title: "Audit · RoadRupee" };

export default function Page() {
  return (
    <ComingSoon
      title="Audit"
      description="Every repair job worth checking, with the work order that shows why."
    >
      <a href="/api/flags.csv" download className={`${buttonVariants()} mt-6 h-12 px-6 text-base`}>
        Download everything worth checking (CSV)
      </a>
    </ComingSoon>
  );
}
