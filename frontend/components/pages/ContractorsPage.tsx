"use client";

import { PageShell } from "@/components/PageShell";
import { ContractorCards } from "@/components/home/ContractorCards";
import { useT } from "@/lib/i18n";

export function ContractorsPage() {
  const t = useT();
  return (
    <PageShell title={t("page.contractors.title")} subtitle={t("page.contractors.sub")}>
      <ContractorCards />
      <p className="mt-6 text-[13px] text-muted-foreground">
        {t("contractor.footer")} {t("common.synthetic")} {t("common.fairNote")}
      </p>
    </PageShell>
  );
}
