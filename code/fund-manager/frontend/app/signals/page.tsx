import { redirect } from "next/navigation";

export default function SignalsPage() {
  redirect("/watchlist?tab=signals");
}
