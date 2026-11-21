import { redirect } from "next/navigation";

// "Ask the auditor" is not built yet. Until it is, send anyone who lands here to Trace my complaint,
// the closest working feature, so nobody meets an unfinished page.
export default function Page() {
  redirect("/trace");
}
