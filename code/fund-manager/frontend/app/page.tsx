import { api } from "@/lib/api";
import { KpiCard } from "@/components/kpi-card";
import { KillSwitchBanner } from "@/components/kill-switch-banner";
import { EquityCurve } from "@/components/equity-curve";
import { SignalsFeed } from "@/components/signals-feed";
import { Badge } from "@/components/ui/badge";

function fmtIDR(v: number) { return `Rp ${(v / 1_000_000).toFixed(1)}M`; }
function fmtPct(v: number) { return `${v?.toFixed(1) ?? 0}%`; }

export default async function Overview() {
  const [current, perfResp, signalsResp, layerResp] = await Promise.allSettled([
    api.getPortfolioCurrent(),
    api.getPerformanceDaily(),
    api.getRecentSignals(),
    api.getLayerOutputs(new Date().toISOString().slice(0, 10)),
  ]);

  const snap = current.status === "fulfilled" ? current.value.snapshot : null;
  const perf = perfResp.status === "fulfilled" ? perfResp.value.items : [];
  const signals = signalsResp.status === "fulfilled" ? signalsResp.value.items.slice(0, 10) : [];
  const layers = layerResp.status === "fulfilled" ? layerResp.value.items : [];

  return (
    <div className="space-y-4">
      <KillSwitchBanner />
      <h1 className="text-lg font-bold text-zinc-200">Overview</h1>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard title="Equity" value={snap ? fmtIDR(snap.equity) : "—"} sub={snap?.posture} />
        <KpiCard title="Cash %" value={snap ? fmtPct(snap.cash / snap.equity * 100) : "—"} />
        <KpiCard title="Drawdown" value={snap ? fmtPct(snap.drawdown) : "—"} className={(snap?.drawdown ?? 0) > 5 ? "border-red-700" : ""} />
        <KpiCard title="Utilization" value={snap ? fmtPct(snap.utilization) : "—"} />
      </div>

      {/* Equity curve + signals */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded p-3">
          <div className="text-xs text-zinc-400 mb-2">Equity (60d)</div>
          <EquityCurve data={perf.slice(-60)} />
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded p-3">
          <div className="text-xs text-zinc-400 mb-2">Live Signals</div>
          <SignalsFeed initial={signals} />
        </div>
      </div>

      {/* Today's layer activity */}
      <div className="bg-zinc-900 border border-zinc-800 rounded p-3">
        <div className="text-xs text-zinc-400 mb-2">Today&apos;s Activity</div>
        {layers.length === 0 && <div className="text-sm text-zinc-500">No layer outputs today</div>}
        {layers.map((lo) => (
          <div key={lo.id} className="flex items-start gap-3 py-1.5 border-b border-zinc-800 text-sm">
            <Badge variant="outline" className="shrink-0 text-xs">{lo.layer}</Badge>
            <span className="text-zinc-300">{lo.summary}</span>
            <span className="text-zinc-600 ml-auto text-xs">{lo.ts?.slice(11, 16)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
