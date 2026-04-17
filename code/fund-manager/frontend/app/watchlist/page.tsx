import { api } from "@/lib/api";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";

export default async function Watchlist({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const { status } = await searchParams;
  const data = await api.getWatchlist(status).catch(() => ({ items: [], count: 0 }));

  const convBadge = (c: string) => c === "high" ? "destructive" : c === "med" ? "secondary" : "outline";

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold">Watchlist</h1>
        <div className="flex gap-2 text-sm">
          {["", "active", "hold", "sold", "archived"].map((s) => (
            <Link key={s} href={s ? `?status=${s}` : "/watchlist"}
              className={`px-2 py-0.5 rounded ${status === s || (!status && !s) ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"}`}>
              {s || "all"}
            </Link>
          ))}
        </div>
      </div>

      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-zinc-500 border-b border-zinc-800 text-left text-xs">
            {["Ticker","Added","Status","Conviction","Themes","Notes"].map(h => (
              <th key={h} className="py-1.5 pr-4">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.items.map((w) => (
            <tr key={w.ticker} className="border-b border-zinc-900 hover:bg-zinc-900">
              <td className="py-1.5 pr-4">
                <Link href={`/ticker/${w.ticker}`} className="text-cyan-400 hover:underline">{w.ticker}</Link>
              </td>
              <td className="pr-4 text-zinc-400">{w.first_added}</td>
              <td className="pr-4"><Badge variant="outline" className="text-xs">{w.status}</Badge></td>
              <td className="pr-4">{w.conviction && <Badge variant={convBadge(w.conviction) as "destructive"|"secondary"|"outline"} className="text-xs">{w.conviction}</Badge>}</td>
              <td className="pr-4 text-zinc-400 text-xs">{w.themes}</td>
              <td className="pr-4 text-zinc-500 text-xs">{w.notes?.slice(0, 60)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.items.length === 0 && <div className="text-zinc-500 text-sm py-4">No entries</div>}
    </div>
  );
}
