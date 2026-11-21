import { ContractorPage } from "@/components/contractor/ContractorPage";

export default async function Page({ params }: PageProps<"/contractor/[id]">) {
  const { id } = await params;
  return <ContractorPage id={id} />;
}
