import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

async function getConfluence() {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8787/api/v1";
  const res = await fetch(`${base}/confluence/latest`, { cache: "no-store" });
  if (!res.ok) return { items: [], count: 0 };
  return res.json();
}

const bucketColor = (bucket: string) => {
  if (bucket === "execute") return "success";
  if (bucket === "plan") return "secondary";
  if (bucket === "watch") return "warning";
  return "outline";
};

export default async function ConfluencePage() {
  const data = await getConfluence();

  return (
    <div className="page-shell">
      <section className="page-header">
        <div className="space-y-2">
          <div className="section-label">Scoring model</div>
          <h1 className="page-title">Confluence scores</h1>
          <p className="page-description">Latest aggregate confluence score per ticker, recalculated each L3 cycle.</p>
        </div>
        <Badge variant="secondary">{data.count} rows</Badge>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.items.map((item: any) => {
          let components: Record<string, number> = {};
          try {
            components = JSON.parse(item.components_json);
          } catch {}

          return (
            <Card key={item.id}>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <Link href={`/ticker/${item.ticker}`} className="ticker-link text-base">{item.ticker}</Link>
                  <div className="flex items-center gap-2">
                    <span className="text-3xl font-semibold tracking-[-0.03em] text-foreground">{item.score}</span>
                    <Badge variant={bucketColor(item.bucket) as "success" | "secondary" | "warning" | "outline"}>{item.bucket}</Badge>
                  </div>
                </div>
                <CardDescription>{item.ts?.slice(0, 16)}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {Object.entries(components).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between rounded-xl border border-border/70 bg-secondary/35 px-3 py-2 text-sm">
                    <span className="text-muted-foreground">{key}</span>
                    <span className={Number(value) >= 0 ? "data-positive" : "data-negative"}>{Number(value) > 0 ? "+" : ""}{value}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })}
        {data.items.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No scores yet.</div> : null}
      </div>
    </div>
  );
}
