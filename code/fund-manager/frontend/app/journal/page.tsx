import { redirect } from "next/navigation";

export default function JournalPage() {
  redirect("/portfolio?tab=journal");
}
