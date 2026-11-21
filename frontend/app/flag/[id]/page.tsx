import { EvidencePage } from "@/components/evidence/EvidencePage";

export default async function Page({ params }: PageProps<"/flag/[id]">) {
  const { id } = await params;
  return <EvidencePage id={id} />;
}
