import Link from "next/link";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function fmtIDR(v?: number | null) {
  return typeof v === "number" ? `${(v / 1_000_000).toFixed(1)}M` : "—";
}

function fmtNum(v?: number | null) {
  return typeof v === "number" ? v.toLocaleString() : "—";
}

function tabClass(active: boolean) {
  return `inline-flex items-center rounded-full border px-3 py-1.5 text-sm font-medium transition-all ${active ? "border-primary/30 bg-primary/14 text-foreground shadow-[0_0_0_1px_rgba(113,112,255,0.08)]" : "border-border/70 bg-secondary/45 text-muted-foreground hover:border-border hover:bg-secondary hover:text-foreground"}`;
}

export default async function Watchlist({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string; status?: string; layer?: string; kind?: string; days?: string; plans?: string }>;
}) {
  const { tab, status, layer, kind, days, plans } = await searchParams;
  const activeTab = ["watchlist", "trade-plans", "signals"].includes(tab || "") ? tab! : "watchlist";
  const plansTab = ["today", "queue", "executed", "expired"].includes(plans || "") ? plans! : "today";
  const since = days ? new Date(Date.now() - Number(days) * 86400000).toISOString() : undefined;
  const today = new Date().toISOString().slice(0, 10);

  const [watchlistResp, todayPlansResp, queueResp, execResp, expResp, signalsResp] = await Promise.allSettled([
    api.getWatchlist(status),
    api.getTradePlans(today),
    api.getTradePlans(undefined, undefined, "queued"),
    api.getTradePlans(undefined, undefined, "executed"),
    api.getTradePlans(undefined, undefined, "expired"),
    api.getSignals(undefined, layer, kind, since, 200),
  ]);

  const watchlist = watchlistResp.status === "fulfilled" ? watchlistResp.value : { items: [], count: 0 };
  const todayPlans = todayPlansResp.status === "fulfilled" ? todayPlansResp.value.items : [];
  const queuePlans = queueResp.status === "fulfilled" ? queueResp.value.items : [];
  const execPlans = execResp.status === "fulfilled" ? execResp.value.items : [];
  const expPlans = expResp.status === "fulfilled" ? expResp.value.items : [];
  const signals = signalsResp.status === "fulfilled" ? signalsResp.value : { items: [], count: 0 };

  const convictionVariant = (value: string) => {
    if (value === "high") return "destructive";
    if (value === "med") return "warning";
    return "outline";
  };

  const levelVariant = (level: string) => (level === "alert" ? "destructive" : "secondary");

  const severityVariant = (severity: string) => {
    if (severity === "high") return "destructive";
    if (severity === "medium") return "warning";
    return "outline";
  };

  const currentPlans = plansTab === "today" ? todayPlans : plansTab === "queue" ? queuePlans : plansTab === "executed" ? execPlans : expPlans;

  return (
    <div className="page-shell">
      <section className="page-header">
        <div className="space-y-2">
          <div className="section-label">Idea workspace</div>
          <h1 className="page-title">Watchlist</h1>
          <p className="page-description">Watchlist, trade plans, and signals in one cleaner workflow page.</p>
        </div>
        <Badge variant="secondary">{watchlist.count} names</Badge>
      </section>

      <div className="flex flex-wrap gap-2">
        <Link href="/watchlist?tab=watchlist" className={tabClass(activeTab === "watchlist")}>Watchlist</Link>
        <Link href="/watchlist?tab=trade-plans" className={tabClass(activeTab === "trade-plans")}>Trade Plans</Link>
        <Link href="/watchlist?tab=signals" className={tabClass(activeTab === "signals")}>Signals ({signals.count})</Link>
      </div>

      {activeTab === "watchlist" ? (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Status filters</CardTitle>
              <CardDescription>Quick slices for active, hold, sold, and archived names.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {["", "active", "hold", "sold", "archived"].map((value) => {
                const active = status === value || (!status && !value);
                return (
                  <Link
                    key={value || "all"}
                    href={value ? `?tab=watchlist&status=${value}` : "/watchlist?tab=watchlist"}
                    className={`filter-chip ${active ? "filter-chip-active" : ""}`}
                  >
                    {value || "all"}
                  </Link>
                );
              })}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Watchlist table</CardTitle>
              <CardDescription>Latest watchlist state with conviction and notes.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    {["Ticker", "Added", "Status", "Conviction", "Themes", "Notes"].map((header) => (
                      <TableHead key={header}>{header}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {watchlist.items.map((item) => (
                    <TableRow key={item.ticker}>
                      <TableCell>
                        <Link href={`/ticker/${item.ticker}`} className="ticker-link">{item.ticker}</Link>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{item.first_added}</TableCell>
                      <TableCell><Badge variant="outline">{item.status}</Badge></TableCell>
                      <TableCell>
                        {item.conviction ? <Badge variant={convictionVariant(item.conviction) as "destructive" | "warning" | "outline"}>{item.conviction}</Badge> : "—"}
                      </TableCell>
                      <TableCell className="max-w-80 whitespace-normal text-sm text-muted-foreground">{item.themes || "—"}</TableCell>
                      <TableCell className="max-w-80 whitespace-normal text-sm text-muted-foreground">{item.notes?.slice(0, 100) || "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {watchlist.items.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No watchlist entries.</div> : null}
            </CardContent>
          </Card>
        </div>
      ) : null}

      {activeTab === "trade-plans" ? (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Link href="/watchlist?tab=trade-plans&plans=today" className={tabClass(plansTab === "today")}>Today ({todayPlans.length})</Link>
            <Link href="/watchlist?tab=trade-plans&plans=queue" className={tabClass(plansTab === "queue")}>Queue ({queuePlans.length})</Link>
            <Link href="/watchlist?tab=trade-plans&plans=executed" className={tabClass(plansTab === "executed")}>Executed ({execPlans.length})</Link>
            <Link href="/watchlist?tab=trade-plans&plans=expired" className={tabClass(plansTab === "expired")}>Expired ({expPlans.length})</Link>
          </div>

          <div className="space-y-3">
            {currentPlans.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No plans.</div> : null}
            {currentPlans.map((plan) => (
              <Card key={plan.id}>
                <CardHeader>
                  <div className="flex flex-wrap items-center gap-2">
                    <Link href={`/ticker/${plan.ticker}`} className="ticker-link text-base">{plan.ticker}</Link>
                    <Badge variant="outline">{plan.mode}</Badge>
                    <Badge variant={levelVariant(plan.level) as "destructive" | "secondary"}>{plan.level}</Badge>
                    <span className="text-sm text-muted-foreground">{plan.setup_type || "No setup tag"}</span>
                    <span className="mono ml-auto text-xs text-muted-foreground">{fmtIDR(plan.size_value)} · {plan.risk_pct?.toFixed(1)}% risk</span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid gap-3 text-sm md:grid-cols-3">
                    <div className="rounded-xl border border-border/70 bg-secondary/35 px-3 py-2">
                      <div className="section-label">Entry</div>
                      <div className="mono mt-1 text-foreground">{fmtNum(plan.entry_low)}–{fmtNum(plan.entry_high)}</div>
                    </div>
                    <div className="rounded-xl border border-border/70 bg-secondary/35 px-3 py-2">
                      <div className="section-label">Stop</div>
                      <div className="mono mt-1 data-negative">{fmtNum(plan.stop)}</div>
                    </div>
                    <div className="rounded-xl border border-border/70 bg-secondary/35 px-3 py-2">
                      <div className="section-label">Target 1</div>
                      <div className="mono mt-1 data-positive">{fmtNum(plan.target_1)}</div>
                    </div>
                  </div>
                  <div className="content-block">{plan.raw_md}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : null}

      {activeTab === "signals" ? (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Signal filters</CardTitle>
              <CardDescription>Preset slices for common layer and kind scans.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {[["layer", "L1", "L2", "L3", "L4"], ["kind", "accumulation_setup", "distribution_setup", "spring", "tape_state"]].map(([key, ...values]) => (
                <div key={key} className="flex flex-wrap items-center gap-2">
                  <span className="section-label">{key}</span>
                  {values.map((value) => {
                    const href = key === "layer"
                      ? `?tab=signals&layer=${value}${kind ? `&kind=${kind}` : ""}${days ? `&days=${days}` : ""}`
                      : `?tab=signals&kind=${value}${layer ? `&layer=${layer}` : ""}${days ? `&days=${days}` : ""}`;
                    return <Link key={value} href={href} className="filter-chip">{value}</Link>;
                  })}
                </div>
              ))}
              <Link href="/watchlist?tab=signals" className="filter-chip ml-auto">Clear</Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Signal table</CardTitle>
              <CardDescription>Latest 200 signal rows with payload preview.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    {["Time", "Ticker", "Layer", "Kind", "Severity", "Price", "Context"].map((header) => <TableHead key={header}>{header}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {signals.items.map((signal) => (
                    <TableRow key={signal.id}>
                      <TableCell className="mono text-xs text-muted-foreground">{signal.ts?.slice(0, 16)}</TableCell>
                      <TableCell><Link href={`/ticker/${signal.ticker}`} className="ticker-link">{signal.ticker}</Link></TableCell>
                      <TableCell className="text-muted-foreground">{signal.layer}</TableCell>
                      <TableCell><Badge variant="outline">{signal.kind}</Badge></TableCell>
                      <TableCell><Badge variant={severityVariant(signal.severity) as "destructive" | "warning" | "outline"}>{signal.severity}</Badge></TableCell>
                      <TableCell>{signal.price ? signal.price.toLocaleString() : "—"}</TableCell>
                      <TableCell className="max-w-80 whitespace-normal text-xs text-muted-foreground">{signal.payload_json?.slice(0, 100) || "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {signals.items.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No signals.</div> : null}
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
