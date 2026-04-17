import { api } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

function fmtIDR(v: number) { return v ? `${(v / 1_000_000).toFixed(1)}M` : "—"; }

export default async function TradePlans() {
  const today = new Date().toISOString().slice(0, 10);
  const [todayResp, queueResp, execResp, expResp] = await Promise.allSettled([
    api.getTradePlans(today),
    api.getTradePlans(undefined, undefined, "queued"),
    api.getTradePlans(undefined, undefined, "executed"),
    api.getTradePlans(undefined, undefined, "expired"),
  ]);

  const todayPlans = todayResp.status === "fulfilled" ? todayResp.value.items : [];
  const queuePlans = queueResp.status === "fulfilled" ? queueResp.value.items : [];
  const execPlans = execResp.status === "fulfilled" ? execResp.value.items : [];
  const expPlans = expResp.status === "fulfilled" ? expResp.value.items : [];

  const PlanTable = ({ plans }: { plans: typeof todayPlans }) => (
    <div className="space-y-2">
      {plans.length === 0 && <div className="text-zinc-500 text-sm py-2">No plans</div>}
      {plans.map((p) => (
        <details key={p.id} className="border border-zinc-800 rounded bg-zinc-900">
          <summary className="px-3 py-2 cursor-pointer flex items-center gap-3 text-sm">
            <Link href={`/ticker/${p.ticker}`} className="text-cyan-400 hover:underline font-bold w-16">{p.ticker}</Link>
            <Badge variant="outline" className="text-xs">{p.mode}</Badge>
            <span className="text-zinc-400">{p.setup_type || "—"}</span>
            <span className="text-zinc-300">E: {p.entry_low.toLocaleString()}–{p.entry_high.toLocaleString()}</span>
            <span className="text-red-400">SL: {p.stop.toLocaleString()}</span>
            <span className="text-green-400">T1: {p.target_1.toLocaleString()}</span>
            <span className="text-zinc-400 ml-auto">{fmtIDR(p.size_value)} · {p.risk_pct?.toFixed(1)}% risk</span>
            <Badge variant={p.level === "alert" ? "destructive" : "secondary"} className="text-xs">{p.level}</Badge>
          </summary>
          <div className="px-3 pb-3 pt-1 text-xs text-zinc-400 whitespace-pre-wrap font-mono border-t border-zinc-800 mt-1">
            {p.raw_md}
          </div>
        </details>
      ))}
    </div>
  );

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Trade Plans</h1>
      <Tabs defaultValue="today">
        <TabsList className="bg-zinc-900">
          <TabsTrigger value="today">Today ({todayPlans.length})</TabsTrigger>
          <TabsTrigger value="queue">Queue ({queuePlans.length})</TabsTrigger>
          <TabsTrigger value="executed">Executed ({execPlans.length})</TabsTrigger>
          <TabsTrigger value="expired">Expired ({expPlans.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="today"><PlanTable plans={todayPlans} /></TabsContent>
        <TabsContent value="queue"><PlanTable plans={queuePlans} /></TabsContent>
        <TabsContent value="executed"><PlanTable plans={execPlans} /></TabsContent>
        <TabsContent value="expired"><PlanTable plans={expPlans} /></TabsContent>
      </Tabs>
    </div>
  );
}
