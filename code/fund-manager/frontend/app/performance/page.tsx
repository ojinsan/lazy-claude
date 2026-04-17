import { api } from "@/lib/api";
import { KillSwitchBanner } from "@/components/kill-switch-banner";
import { EquityCurve } from "@/components/equity-curve";
import { KpiCard } from "@/components/kpi-card";

function pct(v: number) { return `${(v ?? 0).toFixed(2)}%`; }

export default async function Performance() {
  const [perfResp, sumResp] = await Promise.allSettled([
    api.getPerformanceDaily(),
    api.getPerformanceSummary(),
  ]);

  const perf = perfResp.status === "fulfilled" ? perfResp.value.items : [];
  const sum = sumResp.status === "fulfilled" ? sumResp.value : {};

  return (
    <div className="space-y-4">
      <KillSwitchBanner />
      <h1 className="text-lg font-bold">Performance</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard title="MTD" value={pct(sum.mtd_return)} />
        <KpiCard title="YTD" value={pct(sum.ytd_return)} />
        <KpiCard title="Alpha" value={pct(sum.alpha)} />
        <KpiCard title="Win Rate 90d" value={pct(sum.win_rate_90d)} />
        <KpiCard title="Avg R 90d" value={sum.avg_r_90d?.toFixed(2) ?? "—"} />
        <KpiCard title="Expectancy 90d" value={pct(sum.expectancy_90d)} />
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded p-3">
        <div className="text-xs text-zinc-400 mb-2">Equity Curve (all time)</div>
        <EquityCurve data={perf} />
      </div>

      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="text-zinc-500 border-b border-zinc-800 text-left">
            {["Date","Equity","Δ Day","IHSG Δ","Alpha","MTD","YTD","Win 90d"].map(h => <th key={h} className="py-1.5 pr-4">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {perf.slice(-30).reverse().map((p) => (
            <tr key={p.date} className="border-b border-zinc-900">
              <td className="py-1 pr-4 text-zinc-400">{p.date}</td>
              <td className="pr-4">{(p.equity / 1_000_000).toFixed(1)}M</td>
              <td className={`pr-4 ${p.daily_return >= 0 ? "text-green-400" : "text-red-400"}`}>{pct(p.daily_return)}</td>
              <td className={`pr-4 ${p.ihsg_return >= 0 ? "text-green-400" : "text-red-400"}`}>{pct(p.ihsg_return)}</td>
              <td className={`pr-4 ${p.alpha >= 0 ? "text-green-400" : "text-red-400"}`}>{pct(p.alpha)}</td>
              <td className="pr-4">{pct(p.mtd_return)}</td>
              <td className="pr-4">{pct(p.ytd_return)}</td>
              <td className="pr-4">{pct(p.win_rate_90d)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
