import { redirect } from "next/navigation";

export default function TradePlansPage() {
  redirect("/watchlist?tab=trade-plans");
}
