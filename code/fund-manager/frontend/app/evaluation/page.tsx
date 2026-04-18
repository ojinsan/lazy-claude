import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default async function EvaluationPage() {
  const [weeklyResp, monthlyResp] = await Promise.allSettled([api.getEvaluations("weekly"), api.getEvaluations("monthly")]);

  const weekly = weeklyResp.status === "fulfilled" ? weeklyResp.value.items : [];
  const monthly = monthlyResp.status === "fulfilled" ? monthlyResp.value.items : [];

  const EvalList = ({ evals }: { evals: typeof weekly }) => (
    <div className="space-y-3">
      {evals.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No evaluations.</div> : null}
      {evals.map((evaluation) => (
        <Card key={evaluation.id}>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle>{evaluation.period_key}</CardTitle>
              <span className="mono text-xs text-muted-foreground">{evaluation.generated_at?.slice(0, 10)}</span>
            </div>
          </CardHeader>
          <CardContent>
            <div className="content-block">{evaluation.body_md}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  return (
    <div className="page-shell">
      <section className="page-header">
        <div className="space-y-2">
          <div className="section-label">Review cadence</div>
          <h1 className="page-title">Evaluation</h1>
          <p className="page-description">Weekly and monthly generated evaluations with cleaner reading layout.</p>
        </div>
      </section>

      <Tabs defaultValue="weekly">
        <TabsList>
          <TabsTrigger value="weekly">Weekly ({weekly.length})</TabsTrigger>
          <TabsTrigger value="monthly">Monthly ({monthly.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="weekly"><EvalList evals={weekly} /></TabsContent>
        <TabsContent value="monthly"><EvalList evals={monthly} /></TabsContent>
      </Tabs>
    </div>
  );
}
