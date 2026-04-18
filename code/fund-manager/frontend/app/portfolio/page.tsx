import Link from "next/link";
import { api } from "@/lib/api";
import { EquityCurve } from "@/components/equity-curve";
import { KillSwitchBanner } from "@/components/kill-switch-banner";
import { KpiCard } from "@/components/kpi-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function fmtIDR(v: number) {
  return `Rp ${(v / 1_000_000).toFixed(1)}M`;
}

function fmtShortIDR(v: number) {
  return `${(v / 1_000_000).toFixed(2)}M`;
}

function fmtPct(v: number) {
  return `${(v ?? 0).toFixed(2)}%`;
}

function positiveClass(v: number) {
  return v >= 0 ? "data-positive" : "data-negative";
}

function tabClass(active: boolean) {
  return `inline-flex items-center rounded-full border px-3 py-1.5 text-sm font-medium transition-all ${active ? "border-primary/30 bg-primary/14 text-foreground shadow-[0_0_0_1px_rgba(113,112,255,0.08)]" : "border-border/70 bg-secondary/45 text-muted-foreground hover:border-border hover:bg-secondary hover:text-foreground"}`;
}

export default async function Portfolio({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string; journal?: string }>;
}) {
  const { tab, journal } = await searchParams;
  const activeTab = ["overview", "performance", "transactions", "journal"].includes(tab || "") ? tab! : "overview";
  const journalTab = journal === "lessons" ? "lessons" : "daily";
  const today = new Date().toISOString().slice(0, 10);

  const [currentResp, perfResp, summaryResp, transactionsResp, layerResp, lessonsResp] = await Promise.allSettled([
    api.getPortfolioCurrent(),
    api.getPerformanceDaily(),
    api.getPerformanceSummary(),
    api.getTransactions(undefined, 180),
    api.getLayerOutputs(today),
    api.getLessons(undefined, undefined, undefined, 30),
  ]);

  const current = currentResp.status === "fulfilled" ? currentResp.value : { snapshot: null, holdings: [] };
  const perf = perfResp.status === "fulfilled" ? perfResp.value.items : [];
  const sum = summaryResp.status === "fulfilled" ? summaryResp.value : {};
  const transactions = transactionsResp.status === "fulfilled" ? transactionsResp.value.items : [];
  const layers = layerResp.status === "fulfilled" ? layerResp.value.items : [];
  const lessons = lessonsResp.status === "fulfilled" ? lessonsResp.value.items : [];

  const { snapshot: snap, holdings } = current;

  const groupedLayers: Record<string, typeof layers> = {};
  layers.forEach((item) => {
    groupedLayers[item.layer] = [...(groupedLayers[item.layer] || []), item];
  });

  const severityVariant = (severity?: string) => {
    if (severity === "high") return "destructive";
    if (severity === "medium") return "warning";
    return "outline";
  };

  return (
    <div className="page-shell">
      <KillSwitchBanner />

      <section className="page-header">
        <div className="space-y-2">
          <div className="section-label">Book workspace</div>
          <h1 className="page-title">Portfolio</h1>
          <p className="page-description">Current holdings, account performance, transactions, and journal in one place.</p>
        </div>
        {snap ? <Badge variant="secondary">{snap.date}</Badge> : null}
      </section>

      <div className="flex flex-wrap gap-2">
        <Link href="/portfolio?tab=overview" className={tabClass(activeTab === "overview")}>Overview</Link>
        <Link href="/portfolio?tab=performance" className={tabClass(activeTab === "performance")}>Performance</Link>
        <Link href="/portfolio?tab=transactions" className={tabClass(activeTab === "transactions")}>Transactions ({transactions.length})</Link>
        <Link href="/portfolio?tab=journal" className={tabClass(activeTab === "journal")}>Journal</Link>
      </div>

      {activeTab === "overview" ? (
        <div className="space-y-4">
          <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <KpiCard title="Equity" value={snap ? fmtIDR(snap.equity) : "—"} sub="Current account value" />
            <KpiCard title="Cash" value={snap ? fmtPct((snap.cash / snap.equity) * 100) : "—"} sub="Capital waiting on setup" />
            <KpiCard
              title="Drawdown"
              value={snap ? fmtPct(snap.drawdown) : "—"}
              sub="Peak-to-trough pressure"
              className={(snap?.drawdown ?? 0) > 5 ? "border-danger/35" : undefined}
            />
            <KpiCard title="Utilization" value={snap ? fmtPct(snap.utilization) : "—"} sub="Capital in market" />
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.3fr_1fr]">
            <Card>
              <CardHeader>
                <CardTitle>Current holdings</CardTitle>
                <CardDescription>Live position table with cost basis, unrealized P&amp;L, and action tags.</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      {["Ticker", "Shares", "Avg", "Last", "Mkt Val", "P&L", "Action", "Thesis"].map((header) => (
                        <TableHead key={header}>{header}</TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {holdings.map((holding) => (
                      <TableRow key={holding.ticker}>
                        <TableCell>
                          <Link href={`/ticker/${holding.ticker}`} className="ticker-link">{holding.ticker}</Link>
                        </TableCell>
                        <TableCell>{holding.shares.toLocaleString()}</TableCell>
                        <TableCell>{holding.avg_cost.toLocaleString()}</TableCell>
                        <TableCell>{holding.last_price?.toLocaleString() || "—"}</TableCell>
                        <TableCell>{fmtShortIDR(holding.market_value)}</TableCell>
                        <TableCell className={positiveClass(holding.unrealized_pnl)}>{holding.unrealized_pct?.toFixed(1)}%</TableCell>
                        <TableCell><Badge variant="outline">{holding.action || "hold"}</Badge></TableCell>
                        <TableCell className="text-muted-foreground">{holding.thesis_status || "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {holdings.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No holdings.</div> : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent system activity</CardTitle>
                <CardDescription>Latest layer outputs for current trading day.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {layers.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No layer outputs today.</div> : null}
                {layers.slice(0, 10).map((item) => (
                  <div key={item.id} className="flex items-start gap-3 rounded-xl border border-border/70 bg-secondary/35 px-4 py-3 text-sm">
                    <Badge variant="outline" className="shrink-0">{item.layer}</Badge>
                    <span className="text-secondary-foreground">{item.summary}</span>
                    <span className="mono ml-auto text-xs text-muted-foreground">{item.ts?.slice(11, 16)}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </section>
        </div>
      ) : null}

      {activeTab === "performance" ? (
        <div className="space-y-4">
          <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <KpiCard title="MTD" value={fmtPct(sum.mtd_return)} />
            <KpiCard title="YTD" value={fmtPct(sum.ytd_return)} />
            <KpiCard title="Alpha" value={fmtPct(sum.alpha)} />
            <KpiCard title="Win Rate 90d" value={fmtPct(sum.win_rate_90d)} />
            <KpiCard title="Avg R 90d" value={sum.avg_r_90d?.toFixed(2) ?? "—"} />
            <KpiCard title="Expectancy 90d" value={fmtPct(sum.expectancy_90d)} />
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Equity curve</CardTitle>
              <CardDescription>All-time account and benchmark movement.</CardDescription>
            </CardHeader>
            <CardContent>
              <EquityCurve data={perf} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent daily rows</CardTitle>
              <CardDescription>Last 30 observations with daily and benchmark deltas.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    {["Date", "Equity", "Δ Day", "IHSG Δ", "Alpha", "MTD", "YTD", "Win 90d"].map((header) => (
                      <TableHead key={header}>{header}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {perf.slice(-30).reverse().map((row) => (
                    <TableRow key={row.date}>
                      <TableCell className="text-muted-foreground">{row.date}</TableCell>
                      <TableCell>{(row.equity / 1_000_000).toFixed(1)}M</TableCell>
                      <TableCell className={row.daily_return >= 0 ? "data-positive" : "data-negative"}>{fmtPct(row.daily_return)}</TableCell>
                      <TableCell className={row.ihsg_return >= 0 ? "data-positive" : "data-negative"}>{fmtPct(row.ihsg_return)}</TableCell>
                      <TableCell className={row.alpha >= 0 ? "data-positive" : "data-negative"}>{fmtPct(row.alpha)}</TableCell>
                      <TableCell>{fmtPct(row.mtd_return)}</TableCell>
                      <TableCell>{fmtPct(row.ytd_return)}</TableCell>
                      <TableCell>{fmtPct(row.win_rate_90d)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {activeTab === "transactions" ? (
        <Card>
          <CardHeader>
            <CardTitle>Transaction history</CardTitle>
            <CardDescription>Portfolio-wide execution history over last 180 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  {["Time", "Ticker", "Side", "Shares", "Price", "P&L", "Layer", "Notes"].map((header) => (
                    <TableHead key={header}>{header}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((tx) => (
                  <TableRow key={tx.id}>
                    <TableCell className="mono text-xs text-muted-foreground">{tx.ts?.slice(0, 16)}</TableCell>
                    <TableCell>
                      <Link href={`/ticker/${tx.ticker}`} className="ticker-link">{tx.ticker}</Link>
                    </TableCell>
                    <TableCell className={tx.side === "BUY" ? "data-positive" : "data-negative"}>{tx.side}</TableCell>
                    <TableCell>{tx.shares.toLocaleString()}</TableCell>
                    <TableCell>{tx.price.toLocaleString()}</TableCell>
                    <TableCell className={tx.pnl > 0 ? "data-positive" : tx.pnl < 0 ? "data-negative" : "text-muted-foreground"}>
                      {tx.pnl ? `${tx.pnl_pct?.toFixed(1)}%` : "open"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{tx.layer_origin || "—"}</TableCell>
                    <TableCell className="max-w-72 whitespace-normal text-sm text-muted-foreground">{tx.notes || "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {transactions.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No transactions.</div> : null}
          </CardContent>
        </Card>
      ) : null}

      {activeTab === "journal" ? (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Link href="/portfolio?tab=journal&journal=daily" className={tabClass(journalTab === "daily")}>Daily</Link>
            <Link href="/portfolio?tab=journal&journal=lessons" className={tabClass(journalTab === "lessons")}>Lessons ({lessons.length})</Link>
          </div>

          {journalTab === "daily" ? (
            <div className="space-y-4">
              {Object.entries(groupedLayers).map(([layer, items]) => (
                <Card key={layer}>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{layer}</Badge>
                      <CardDescription>{items.length} entries</CardDescription>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {items.map((item) => (
                      <div key={item.id} className="rounded-xl border border-border/70 bg-secondary/35 px-4 py-3 text-sm">
                        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                          <span className="mono">{item.ts?.slice(11, 16)}</span>
                          {item.severity ? <Badge variant={severityVariant(item.severity) as "destructive" | "warning" | "outline"}>{item.severity}</Badge> : null}
                        </div>
                        <div className="mt-2 text-secondary-foreground">{item.summary}</div>
                        {item.body_md ? <div className="content-block mt-3">{item.body_md}</div> : null}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ))}
              {layers.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No layer outputs today.</div> : null}
            </div>
          ) : null}

          {journalTab === "lessons" ? (
            <div className="space-y-3">
              {lessons.map((lesson) => (
                <Card key={lesson.id}>
                  <CardContent className="space-y-2 pt-5">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <Badge variant={severityVariant(lesson.severity) as "destructive" | "warning" | "outline"}>{lesson.severity}</Badge>
                      <span className="text-muted-foreground">{lesson.category}</span>
                      {lesson.pattern_tag ? <span className="text-muted-foreground">#{lesson.pattern_tag}</span> : null}
                      <span className="mono ml-auto text-muted-foreground">{lesson.date}</span>
                    </div>
                    <div className="text-sm text-secondary-foreground">{lesson.lesson_text}</div>
                    {lesson.tickers ? (
                      <div className="flex flex-wrap gap-2">
                        {lesson.tickers.split(",").map((ticker) => (
                          <Link key={ticker} href={`/ticker/${ticker}`} className="filter-chip">{ticker}</Link>
                        ))}
                      </div>
                    ) : null}
                  </CardContent>
                </Card>
              ))}
              {lessons.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No lessons in last 30 days.</div> : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
