import { redirect } from "next/navigation";

// Contractor scorecards live at /contractors (report cards). Keep the old URL working.
export default function Page() {
  redirect("/contractors");
}
