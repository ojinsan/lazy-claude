import Link from "next/link";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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
    <div className="page-shell">
      <section className="page-header">
        <div className="space-y-3">
          <Link href="/portfolio" className="text-sm text-muted-foreground hover:text-foreground">← Back to portfolio</Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="page-title">{t}</h1>
            {thesis ? <Badge variant="outline">{thesis.status}</Badge> : null}
          </div>
          <p className="page-description">Single-name workspace for thesis, plans, signals, and transaction history.</p>
        </div>
        {latestHolding ? (
          <div className="rounded-2xl border border-border/80 bg-card px-4 py-3 text-sm shadow-[0_0_0_1px_rgba(255,255,255,0.02),0_18px_40px_rgba(0,0,0,0.22)]">
            <div className="section-label">Current holding</div>
            <div className="mt-2 flex flex-wrap gap-3 text-secondary-foreground">
              <span>{latestHolding.shares.toLocaleString()} shares</span>
              <span>avg {latestHolding.avg_cost.toLocaleString()}</span>
              <span className={latestHolding.unrealized_pnl >= 0 ? "data-positive" : "data-negative"}>{latestHolding.unrealized_pct?.toFixed(1)}%</span>
            </div>
          </div>
        ) : null}
      </section>

      <Tabs defaultValue="thesis">
        <TabsList>
          <TabsTrigger value="thesis">Thesis</TabsTrigger>
          <TabsTrigger value="plans">Plans ({plans.length})</TabsTrigger>
          <TabsTrigger value="signals">Signals ({signals.length})</TabsTrigger>
          <TabsTrigger value="transactions">Transactions ({txs.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="thesis">
          <Card>
            <CardHeader>
              <CardTitle>Thesis</CardTitle>
              <CardDescription>{thesis ? `Last review: ${thesis.last_review || "—"}` : `No thesis for ${t}.`}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {thesis ? (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{thesis.status}</Badge>
                    <span className="text-xs text-muted-foreground">{t}</span>
                  </div>
                  <div className="content-block">{thesis.body_md}</div>
                  <div className="space-y-2">
                    <div className="section-label">Review log</div>
                    {reviews.map((review) => (
                      <div key={review.id} className="rounded-xl border border-border/70 bg-secondary/35 px-4 py-3 text-sm">
                        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                          <span>{review.review_date}</span>
                          <span>•</span>
                          <span>{review.layer}</span>
                        </div>
                        <div className="mt-1 text-secondary-foreground">{review.note}</div>
                      </div>
                    ))}
                    {reviews.length === 0 ? <div className="text-sm text-muted-foreground">No reviews yet.</div> : null}
                  </div>
                </>
              ) : (
                <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No thesis for {t}.</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="plans">
          <Card>
            <CardHeader>
              <CardTitle>Trade plans</CardTitle>
              <CardDescription>Queued and historical setups tied to this ticker.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {plans.map((plan) => (
                <div key={plan.id} className="rounded-2xl border border-border/80 bg-secondary/35 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{plan.plan_date}</Badge>
                    <Badge variant="secondary">{plan.mode}</Badge>
                    <span className="text-sm text-muted-foreground">{plan.setup_type || "No setup tag"}</span>
                    <Badge variant={plan.status === "executed" ? "success" : "outline"} className="ml-auto">{plan.status}</Badge>
                  </div>
                  <div className="mt-3 grid gap-3 text-sm md:grid-cols-3">
                    <div><span className="section-label">Entry</span><div className="mono mt-1">{plan.entry_low.toLocaleString()}–{plan.entry_high.toLocaleString()}</div></div>
                    <div><span className="section-label">Stop</span><div className="mono mt-1 data-negative">{plan.stop.toLocaleString()}</div></div>
                    <div><span className="section-label">Target 1</span><div className="mono mt-1 data-positive">{plan.target_1.toLocaleString()}</div></div>
                  </div>
                  <div className="content-block mt-3">{plan.raw_md?.slice(0, 400)}</div>
                </div>
              ))}
              {plans.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No plans.</div> : null}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="signals">
          <Card>
            <CardHeader>
              <CardTitle>Signals</CardTitle>
              <CardDescription>Latest signal events linked to {t}.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    {["Time", "Layer", "Kind", "Severity", "Price"].map((header) => <TableHead key={header}>{header}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {signals.map((signal) => (
                    <TableRow key={signal.id}>
                      <TableCell className="mono text-xs text-muted-foreground">{signal.ts?.slice(0, 16)}</TableCell>
                      <TableCell className="text-muted-foreground">{signal.layer}</TableCell>
                      <TableCell><Badge variant="outline">{signal.kind}</Badge></TableCell>
                      <TableCell className="capitalize text-secondary-foreground">{signal.severity}</TableCell>
                      <TableCell>{signal.price?.toLocaleString() || "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {signals.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No signals.</div> : null}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="transactions">
          <Card>
            <CardHeader>
              <CardTitle>Transactions</CardTitle>
              <CardDescription>Execution history over last 365 days.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    {["Time", "Side", "Shares", "Price", "P&L", "Layer"].map((header) => <TableHead key={header}>{header}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {txs.map((tx) => (
                    <TableRow key={tx.id}>
                      <TableCell className="mono text-xs text-muted-foreground">{tx.ts?.slice(0, 16)}</TableCell>
                      <TableCell className={tx.side === "BUY" ? "data-positive" : "data-negative"}>{tx.side}</TableCell>
                      <TableCell>{tx.shares.toLocaleString()}</TableCell>
                      <TableCell>{tx.price.toLocaleString()}</TableCell>
                      <TableCell className={tx.pnl > 0 ? "data-positive" : tx.pnl < 0 ? "data-negative" : "text-muted-foreground"}>
                        {tx.pnl ? `${tx.pnl_pct?.toFixed(1)}%` : "open"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{tx.layer_origin}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {txs.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No transactions.</div> : null}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
