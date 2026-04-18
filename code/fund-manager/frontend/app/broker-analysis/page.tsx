import { redirect } from "next/navigation";

export default function BrokerAnalysisPage() {
  redirect("/screener?tab=tape");
}
