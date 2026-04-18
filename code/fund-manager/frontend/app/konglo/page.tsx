import * as fs from "fs";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type KongloGroup = { id: string; name: string; owner: string; market_power: string; sectors: string; };
type KongloStock = { ticker: string; category: string; notes?: string; };

function loadKongloData(): { conglomerates: Array<{ id: string; name: string; owner: string; market_power: string; sectors: string[]; stocks: KongloStock[] }> } | null {
  const jsonPath = "/home/lazywork/workspace/tools/trader/data/konglo_list.json";
  try {
    return JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
  } catch {
    return null;
  }
}

async function getKongloGroups(): Promise<{ items: KongloGroup[]; count: number }> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8787/api/v1";
  const res = await fetch(`${base}/konglo/groups`, { cache: "no-store" });
  if (!res.ok) return { items: [], count: 0 };
  return res.json();
}

export default async function KongloPage() {
  const dbGroups = await getKongloGroups();
  const raw = loadKongloData();
  const groups = raw?.conglomerates ?? [];

  const powerVariant = (power: string) => {
    if (power === "high") return "success";
    if (power === "med") return "warning";
    return "outline";
  };

  return (
    <div className="page-shell">
      <section className="page-header">
        <div className="space-y-2">
          <div className="section-label">Ownership map</div>
          <h1 className="page-title">Konglo groups</h1>
          <p className="page-description">Conglomerate clusters with linked tickers, sectors, and market power labels.</p>
        </div>
        <Badge variant="secondary">{groups.length || dbGroups.count} groups</Badge>
      </section>

      <div className="space-y-4">
        {groups.map((group) => (
          <Card key={group.id}>
            <CardHeader>
              <div className="flex flex-wrap items-start gap-3">
                <div className="space-y-2">
                  <CardTitle>{group.name}</CardTitle>
                  <CardDescription>Sectors: {group.sectors.join(", ")}</CardDescription>
                </div>
                <Badge variant="outline">{group.owner}</Badge>
                <Badge variant={powerVariant(group.market_power) as "success" | "warning" | "outline"}>{group.market_power}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {group.stocks.map((stock) => (
                  <Link key={stock.ticker} href={`/ticker/${stock.ticker}`} className="filter-chip">{stock.ticker}</Link>
                ))}
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {group.stocks.map((stock) => (
                  <div key={stock.ticker} className="rounded-xl border border-border/70 bg-secondary/35 px-3 py-2 text-sm">
                    <div className="flex items-center gap-2">
                      <Link href={`/ticker/${stock.ticker}`} className="ticker-link">{stock.ticker}</Link>
                      <span className="text-muted-foreground">{stock.category}</span>
                    </div>
                    {stock.notes ? <div className="mt-1 text-xs text-muted-foreground">{stock.notes}</div> : null}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {groups.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">Loading from konglo_list.json — {dbGroups.count} groups in DB.</div> : null}
    </div>
  );
}
