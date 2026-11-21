import { Suspense } from "react";
import { WardPage } from "@/components/ward/WardPage";

export default async function Page({ params }: PageProps<"/ward/[slug]">) {
  const { slug } = await params;
  return (
    <Suspense>
      <WardPage slug={slug} />
    </Suspense>
  );
}
