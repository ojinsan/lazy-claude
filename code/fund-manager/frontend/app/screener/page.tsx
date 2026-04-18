import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

async function getTapeStates(ticker?: string) {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8787/api/v1";
  const url = new URL(`${base}/tape-states`);
  if (ticker) url.searchParams.set("ticker", ticker);
  url.searchParams.set("limit", "100");
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) return { items: [], count: 0 };
  return res.json();
}

const compositeVariant = (composite: string) => {
  if (composite === "ideal_markup" || composite === "healthy_markup") return "success";
  if (composite === "spring_ready") return "secondary";
  if (composite === "spam_warning") return "warning";
  if (composite === "fake_support" || composite === "distribution_trap") return "destructive";
  return "outline";
};

export default async function ScreenerPage({ searchParams }: { searchParams: Promise<{ ticker?: string; tab?: string }> }) {
  const { ticker, tab } = await searchParams;
  const activeTab = tab === "tape" ? "tape" : "tape";
  const data = await getTapeStates(ticker);

  return (
    <div className="page-shell">
      <section className="page-header">
        <div className="space-y-2">
          <div className="section-label">Screener workspace</div>
          <h1 className="page-title">Screener</h1>
          <p className="page-description">Tape is first module here. More screening features can land in this workspace later.</p>
        </div>
        <Badge variant="secondary">{data.count} rows</Badge>
      </section>

      <Tabs defaultValue={activeTab}>
        <TabsList>
          <TabsTrigger value="tape">Tape</TabsTrigger>
        </TabsList>

        <TabsContent value="tape">
          <Card>
            <CardHeader>
              <CardTitle>Tape states</CardTitle>
              <CardDescription>Live feed from `tape_runner.snapshot`, refreshed each monitoring cycle.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    {["Time", "Ticker", "Composite", "Confidence", "Wall Fate"].map((header) => <TableHead key={header}>{header}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((item: any) => (
                    <TableRow key={item.id}>
                      <TableCell className="mono text-xs text-muted-foreground">{item.ts?.slice(0, 16)}</TableCell>
                      <TableCell className="mono text-foreground">{item.ticker}</TableCell>
                      <TableCell><Badge variant={compositeVariant(item.composite) as "success" | "secondary" | "warning" | "destructive" | "outline"}>{item.composite}</Badge></TableCell>
                      <TableCell><Badge variant="outline">{item.confidence}</Badge></TableCell>
                      <TableCell className="text-muted-foreground">{item.wall_fate || "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {data.items.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No tape states yet.</div> : null}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
