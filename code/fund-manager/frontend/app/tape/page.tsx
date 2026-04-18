import { redirect } from "next/navigation";

export default function TapePage() {
  redirect("/screener?tab=tape");
}
