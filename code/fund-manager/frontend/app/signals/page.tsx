import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export default async function Signals({ searchParams }: { searchParams: Promise<{ ticker?: string; layer?: string; kind?: string; days?: string }> }) {
  const { ticker, layer, kind, days } = await searchParams;
  const since = days ? new Date(Date.now() - Number(days) * 86400000).toISOString() : undefined;
  const data = await api.getSignals(ticker, layer, kind, since, 200).catch(() => ({ items: [], count: 0 }));

  const sevColor = (s: string) => s === "high" ? "text-red-400" : s === "medium" ? "text-yellow-400" : "text-zinc-400";

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Signals — {data.count} total</h1>

      {/* Filter bar */}
      <div className="flex gap-3 text-sm text-zinc-400 flex-wrap">
        {[["layer","L1","L2","L3","L4"],["kind","accumulation_setup","distribution_setup","spring","tape_state"]].map(([key, ...vals]) => (
          <div key={key} className="flex gap-1 items-center">
            <span className="text-zinc-600">{key}:</span>
            {vals.map((v) => (
              <a key={v} href={`?${key}=${v}`} className="px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-xs">{v}</a>
            ))}
          </div>
        ))}
        <a href="/signals" className="text-zinc-600 hover:text-white text-xs ml-auto">clear</a>
      </div>

      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-zinc-500 border-b border-zinc-800 text-left text-xs">
            {["Time","Ticker","Layer","Kind","Severity","Price","Context"].map(h => (
              <th key={h} className="py-1.5 pr-4">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.items.map((s) => (
            <tr key={s.id} className="border-b border-zinc-900 hover:bg-zinc-900">
              <td className="py-1.5 pr-4 text-zinc-500 text-xs">{s.ts?.slice(0, 16)}</td>
              <td className="pr-4"><Link href={`/ticker/${s.ticker}`} className="text-cyan-400 hover:underline">{s.ticker}</Link></td>
              <td className="pr-4 text-zinc-400">{s.layer}</td>
              <td className="pr-4"><Badge variant="outline" className="text-xs">{s.kind}</Badge></td>
              <td className={`pr-4 ${sevColor(s.severity)}`}>{s.severity}</td>
              <td className="pr-4 text-zinc-300">{s.price ? s.price.toLocaleString() : "—"}</td>
              <td className="pr-4 text-zinc-500 text-xs">{s.payload_json?.slice(0, 60)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.items.length === 0 && <div className="text-zinc-500 text-sm py-4">No signals</div>}
    </div>
  );
}
