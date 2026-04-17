import { api } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default async function EvaluationPage() {
  const [weeklyResp, monthlyResp] = await Promise.allSettled([
    api.getEvaluations("weekly"),
    api.getEvaluations("monthly"),
  ]);

  const weekly = weeklyResp.status === "fulfilled" ? weeklyResp.value.items : [];
  const monthly = monthlyResp.status === "fulfilled" ? monthlyResp.value.items : [];

  const EvalList = ({ evals }: { evals: typeof weekly }) => (
    <div className="space-y-3">
      {evals.map((e) => (
        <details key={e.id} className="border border-zinc-800 rounded bg-zinc-900">
          <summary className="px-3 py-2 cursor-pointer flex items-center justify-between text-sm">
            <span className="font-semibold">{e.period_key}</span>
            <span className="text-zinc-500 text-xs">{e.generated_at?.slice(0, 10)}</span>
          </summary>
          <div className="px-3 pb-3 pt-1 border-t border-zinc-800">
            <pre className="text-xs text-zinc-300 whitespace-pre-wrap font-sans">{e.body_md}</pre>
          </div>
        </details>
      ))}
      {evals.length === 0 && <div className="text-zinc-500 text-sm py-4">No evaluations</div>}
    </div>
  );

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Evaluation</h1>
      <Tabs defaultValue="weekly">
        <TabsList className="bg-zinc-900">
          <TabsTrigger value="weekly">Weekly ({weekly.length})</TabsTrigger>
          <TabsTrigger value="monthly">Monthly ({monthly.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="weekly"><EvalList evals={weekly} /></TabsContent>
        <TabsContent value="monthly"><EvalList evals={monthly} /></TabsContent>
      </Tabs>
    </div>
  );
}
