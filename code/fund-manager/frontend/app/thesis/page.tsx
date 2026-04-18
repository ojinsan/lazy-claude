import Link from "next/link";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default async function ThesisPage({ searchParams }: { searchParams: Promise<{ ticker?: string; status?: string }> }) {
  const { ticker, status } = await searchParams;
  const [listResp, selectedResp, reviewsResp] = await Promise.allSettled([
    api.getThesisList(status),
    ticker ? api.getThesis(ticker) : Promise.resolve(null),
    ticker ? api.getThesisReviews(ticker) : Promise.resolve({ items: [], count: 0 }),
  ]);

  const list = listResp.status === "fulfilled" ? listResp.value.items : [];
  const selected = selectedResp.status === "fulfilled" ? selectedResp.value : null;
  const reviews = reviewsResp.status === "fulfilled" ? (reviewsResp.value as { items: any[] }).items : [];

  const statusVariant = (value: string) => {
    if (value === "active") return "success";
    if (value === "closed") return "destructive";
    return "outline";
  };

  return (
    <div className="page-shell">
      <section className="page-header">
        <div className="space-y-2">
          <div className="section-label">Research book</div>
          <h1 className="page-title">Thesis</h1>
          <p className="page-description">Thesis list, selected write-up, and review history.</p>
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        {["active", "closed", "archived"].map((value) => (
          <a key={value} href={`?status=${value}`} className={`filter-chip ${status === value ? "filter-chip-active" : ""}`}>{value}</a>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-[320px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Tickers</CardTitle>
            <CardDescription>Available thesis entries for selected status.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {list.map((item) => (
              <Link
                key={item.ticker}
                href={`?ticker=${item.ticker}${status ? `&status=${status}` : ""}`}
                className={`flex items-center justify-between rounded-xl border px-3 py-2 text-sm transition-colors ${ticker === item.ticker ? "border-primary/30 bg-primary/12" : "border-border/70 bg-secondary/35 hover:bg-secondary/60"}`}
              >
                <span className="mono text-foreground">{item.ticker}</span>
                <Badge variant={statusVariant(item.status) as "success" | "destructive" | "outline"}>{item.status}</Badge>
              </Link>
            ))}
            {list.length === 0 ? <div className="text-sm text-muted-foreground">No thesis.</div> : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle>{selected ? selected.ticker : "Select a ticker"}</CardTitle>
              {selected ? <Badge variant={statusVariant(selected.status) as "success" | "destructive" | "outline"}>{selected.status}</Badge> : null}
            </div>
            <CardDescription>{selected ? `Last review: ${selected.last_review || "—"}` : "Choose a thesis from left column."}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {selected ? (
              <>
                <div className="content-block">{selected.body_md}</div>
                <div className="space-y-2">
                  <div className="section-label">Review log</div>
                  {reviews.map((review: any) => (
                    <div key={review.id} className="rounded-xl border border-border/70 bg-secondary/35 px-4 py-3 text-sm">
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span>{review.review_date}</span>
                        <span>•</span>
                        <span>{review.layer}</span>
                      </div>
                      <div className="mt-1 text-secondary-foreground">{review.note}</div>
                    </div>
                  ))}
                  {reviews.length === 0 ? <div className="text-sm text-muted-foreground">No reviews.</div> : null}
                </div>
              </>
            ) : (
              <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">Select a ticker.</div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
