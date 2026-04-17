import { api } from "@/lib/api";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";

function fmtIDR(v: number) { return `${(v / 1_000_000).toFixed(2)}M`; }
function pctClass(v: number) { return v >= 0 ? "text-green-400" : "text-red-400"; }

export default async function Portfolio() {
  const current = await api.getPortfolioCurrent().catch(() => ({ snapshot: null, holdings: [] }));
  const { snapshot: snap, holdings } = current;

  // sector concentration
  const sectors: Record<string, number> = {};
  holdings.forEach((h) => { sectors[h.sector || "Other"] = (sectors[h.sector || "Other"] || 0) + h.market_value; });

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Portfolio — {snap?.date ?? "—"}</h1>
      {snap && (
        <div className="grid grid-cols-3 gap-2 text-sm text-zinc-400">
          <span>Equity: <b className="text-white">Rp {fmtIDR(snap.equity)}</b></span>
          <span>DD: <b className={pctClass(-snap.drawdown)}>{snap.drawdown.toFixed(1)}%</b></span>
          <span>Posture: <b className="text-white">{snap.posture}</b></span>
        </div>
      )}

      {/* Holdings table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-zinc-500 border-b border-zinc-800 text-left text-xs">
              {["Ticker","Shares","Avg","Last","Mkt Val","P&L","Sector","Action","Thesis"].map(h => (
                <th key={h} className="py-1.5 pr-4">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => (
              <tr key={h.ticker} className="border-b border-zinc-900 hover:bg-zinc-900">
                <td className="py-1.5 pr-4">
                  <Link href={`/ticker/${h.ticker}`} className="text-cyan-400 hover:underline">{h.ticker}</Link>
                </td>
                <td className="pr-4">{h.shares.toLocaleString()}</td>
                <td className="pr-4">{h.avg_cost.toLocaleString()}</td>
                <td className="pr-4">{h.last_price?.toLocaleString() || "—"}</td>
                <td className="pr-4">{fmtIDR(h.market_value)}</td>
                <td className={`pr-4 ${pctClass(h.unrealized_pnl)}`}>{h.unrealized_pct?.toFixed(1)}%</td>
                <td className="pr-4 text-zinc-400">{h.sector || "—"}</td>
                <td className="pr-4"><Badge variant="outline" className="text-xs">{h.action || "hold"}</Badge></td>
                <td className="pr-4 text-zinc-400">{h.thesis_status || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {holdings.length === 0 && <div className="text-zinc-500 text-sm py-4">No holdings</div>}
      </div>

      {/* Sector concentration */}
      <div className="bg-zinc-900 border border-zinc-800 rounded p-3">
        <div className="text-xs text-zinc-400 mb-2">Sector Concentration</div>
        <div className="space-y-1">
          {Object.entries(sectors).sort((a, b) => b[1] - a[1]).map(([s, v]) => (
            <div key={s} className="flex gap-2 text-sm">
              <span className="w-32 text-zinc-400 truncate">{s}</span>
              <span className="text-white">{fmtIDR(v)}</span>
              {snap && <span className="text-zinc-500">{(v / snap.equity * 100).toFixed(0)}%</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
