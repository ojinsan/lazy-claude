import { api } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export default async function TickerPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const t = ticker.toUpperCase();

  const [thesisResp, reviewsResp, plansResp, sigsResp, txResp, holdingResp] = await Promise.allSettled([
    api.getThesis(t).catch(() => null),
    api.getThesisReviews(t),
    api.getTradePlans(undefined, t),
    api.getSignals(t, undefined, undefined, undefined, 50),
    api.getTransactions(t, 365),
    api.getHoldings(undefined, t),
  ]);

  const thesis = thesisResp.status === "fulfilled" ? thesisResp.value : null;
  const reviews = reviewsResp.status === "fulfilled" ? reviewsResp.value.items : [];
  const plans = plansResp.status === "fulfilled" ? plansResp.value.items : [];
  const signals = sigsResp.status === "fulfilled" ? sigsResp.value.items : [];
  const txs = txResp.status === "fulfilled" ? txResp.value.items : [];
  const holdings = holdingResp.status === "fulfilled" ? holdingResp.value.items : [];
  const latestHolding = holdings[0] ?? null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link href="/portfolio" className="text-zinc-500 hover:text-white text-sm">← Portfolio</Link>
        <h1 className="text-xl font-bold text-cyan-400">{t}</h1>
        {latestHolding && (
          <div className="flex gap-3 text-sm text-zinc-400">
            <span>{latestHolding.shares.toLocaleString()} shares</span>
            <span>avg {latestHolding.avg_cost.toLocaleString()}</span>
            <span className={latestHolding.unrealized_pnl >= 0 ? "text-green-400" : "text-red-400"}>
              {latestHolding.unrealized_pct?.toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      <Tabs defaultValue="thesis">
        <TabsList className="bg-zinc-900">
          <TabsTrigger value="thesis">Thesis</TabsTrigger>
          <TabsTrigger value="plans">Plans ({plans.length})</TabsTrigger>
          <TabsTrigger value="signals">Signals ({signals.length})</TabsTrigger>
          <TabsTrigger value="transactions">Transactions ({txs.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="thesis">
          {thesis ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Badge variant="outline">{thesis.status}</Badge>
                <span className="text-zinc-500 text-xs">last review: {thesis.last_review || "—"}</span>
              </div>
              <pre className="text-sm text-zinc-300 whitespace-pre-wrap font-sans bg-zinc-900 rounded p-3 border border-zinc-800">{thesis.body_md}</pre>
              <div>
                <div className="text-xs text-zinc-400 mb-1">Review Log</div>
                {reviews.map((r) => (
                  <div key={r.id} className="text-xs py-1 border-b border-zinc-900">
                    <span className="text-zinc-500">{r.review_date}</span>
                    <span className="text-zinc-600 mx-1">({r.layer})</span>
                    <span className="text-zinc-300">{r.note}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : <div className="text-zinc-500 text-sm py-4">No thesis for {t}</div>}
        </TabsContent>

        <TabsContent value="plans">
          {plans.map((p) => (
            <div key={p.id} className="border border-zinc-800 rounded p-3 mb-2 bg-zinc-900 text-sm space-y-1">
              <div className="flex items-center gap-2">
                <Badge variant="outline">{p.plan_date}</Badge>
                <Badge variant="secondary">{p.mode}</Badge>
                <span className="text-zinc-400">{p.setup_type}</span>
                <Badge variant={p.status === "executed" ? "secondary" : "outline"} className="ml-auto">{p.status}</Badge>
              </div>
              <div className="text-zinc-400 text-xs">Entry: {p.entry_low.toLocaleString()}–{p.entry_high.toLocaleString()} | SL: {p.stop.toLocaleString()} | T1: {p.target_1.toLocaleString()}</div>
              <pre className="text-xs text-zinc-500 whitespace-pre-wrap">{p.raw_md?.slice(0, 200)}</pre>
            </div>
          ))}
          {plans.length === 0 && <div className="text-zinc-500 text-sm py-4">No plans</div>}
        </TabsContent>

        <TabsContent value="signals">
          <table className="w-full text-xs border-collapse">
            <thead><tr className="text-zinc-500 border-b border-zinc-800 text-left">{["Time","Layer","Kind","Severity","Price"].map(h=><th key={h} className="py-1.5 pr-3">{h}</th>)}</tr></thead>
            <tbody>
              {signals.map((s) => (
                <tr key={s.id} className="border-b border-zinc-900">
                  <td className="py-1 pr-3 text-zinc-500">{s.ts?.slice(0, 16)}</td>
                  <td className="pr-3 text-zinc-400">{s.layer}</td>
                  <td className="pr-3"><Badge variant="outline" className="text-xs">{s.kind}</Badge></td>
                  <td className="pr-3">{s.severity}</td>
                  <td className="pr-3">{s.price?.toLocaleString() || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {signals.length === 0 && <div className="text-zinc-500 text-sm py-4">No signals</div>}
        </TabsContent>

        <TabsContent value="transactions">
          <table className="w-full text-xs border-collapse">
            <thead><tr className="text-zinc-500 border-b border-zinc-800 text-left">{["Time","Side","Shares","Price","P&L","Layer"].map(h=><th key={h} className="py-1.5 pr-3">{h}</th>)}</tr></thead>
            <tbody>
              {txs.map((t) => (
                <tr key={t.id} className="border-b border-zinc-900">
                  <td className="py-1 pr-3 text-zinc-500">{t.ts?.slice(0, 16)}</td>
                  <td className={`pr-3 font-semibold ${t.side === "BUY" ? "text-green-400" : "text-red-400"}`}>{t.side}</td>
                  <td className="pr-3">{t.shares.toLocaleString()}</td>
                  <td className="pr-3">{t.price.toLocaleString()}</td>
                  <td className={`pr-3 ${t.pnl >= 0 ? "text-green-400" : t.pnl < 0 ? "text-red-400" : "text-zinc-500"}`}>{t.pnl ? `${t.pnl_pct?.toFixed(1)}%` : "open"}</td>
                  <td className="pr-3 text-zinc-500">{t.layer_origin}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {txs.length === 0 && <div className="text-zinc-500 text-sm py-4">No transactions</div>}
        </TabsContent>
      </Tabs>
    </div>
  );
}
