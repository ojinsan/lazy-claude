import Link from "next/link";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default async function Themes() {
  const data = await api.getThemes().catch(() => ({ items: [], count: 0 }));

  return (
    <div className="page-shell">
      <section className="page-header">
        <div className="space-y-2">
          <div className="section-label">Research clusters</div>
          <h1 className="page-title">Themes</h1>
          <p className="page-description">Grouped market narratives with linked tickers and current status markers.</p>
        </div>
        <Badge variant="secondary">{data.count} themes</Badge>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.items.map((theme) => (
          <Card key={theme.slug} className="h-full">
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-2">
                  <CardTitle>{theme.name}</CardTitle>
                  <CardDescription>{theme.sector || "No sector tag"}</CardDescription>
                </div>
                <Badge variant={theme.status === "active" ? "secondary" : "outline"}>{theme.status}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {theme.related_tickers ? (
                <div className="flex flex-wrap gap-2">
                  {theme.related_tickers
                    .split(",")
                    .filter(Boolean)
                    .map((ticker) => (
                      <Link key={ticker} href={`/ticker/${ticker.trim()}`} className="filter-chip">
                        {ticker.trim()}
                      </Link>
                    ))}
                </div>
              ) : null}
              <div className="content-block min-h-36">{theme.body_md || "No description."}</div>
            </CardContent>
          </Card>
        ))}
        {data.items.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No themes.</div> : null}
      </div>
    </div>
  );
}
