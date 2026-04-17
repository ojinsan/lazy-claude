import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

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

  const statusColor = (s: string) => s === "active" ? "text-green-400" : s === "closed" ? "text-red-400" : "text-zinc-400";

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Thesis</h1>
      <div className="flex gap-2 text-sm mb-2">
        {["active","closed","archived"].map((s) => (
          <a key={s} href={`?status=${s}`} className={`px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-xs ${status===s?"ring-1 ring-zinc-500":""}`}>{s}</a>
        ))}
      </div>
      <div className="grid md:grid-cols-3 gap-4">
        {/* Left: list */}
        <div className="border border-zinc-800 rounded bg-zinc-900 overflow-y-auto max-h-[70vh]">
          {list.map((t) => (
            <Link key={t.ticker} href={`?ticker=${t.ticker}${status?`&status=${status}`:""}`}
              className={`flex items-center justify-between px-3 py-2 border-b border-zinc-800 hover:bg-zinc-800 text-sm ${ticker===t.ticker?"bg-zinc-800":""}`}>
              <span className="font-mono text-cyan-400">{t.ticker}</span>
              <span className={`text-xs ${statusColor(t.status)}`}>{t.status}</span>
            </Link>
          ))}
          {list.length === 0 && <div className="p-3 text-zinc-500 text-sm">No thesis</div>}
        </div>

        {/* Right: selected */}
        <div className="md:col-span-2 border border-zinc-800 rounded bg-zinc-900 p-3 space-y-3 max-h-[70vh] overflow-y-auto">
          {selected ? (
            <>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-cyan-400">{selected.ticker}</span>
                <Badge variant="outline">{selected.status}</Badge>
                <span className="text-zinc-500 text-xs ml-auto">last review: {selected.last_review || "—"}</span>
              </div>
              <pre className="text-sm text-zinc-300 whitespace-pre-wrap font-sans">{selected.body_md}</pre>
              <div className="border-t border-zinc-700 pt-2">
                <div className="text-xs text-zinc-400 mb-1">Review Log</div>
                {reviews.map((r: any) => (
                  <div key={r.id} className="text-xs py-1 border-b border-zinc-900">
                    <span className="text-zinc-500">{r.review_date}</span>
                    <span className="text-zinc-600 mx-1">({r.layer})</span>
                    <span className="text-zinc-300">{r.note}</span>
                  </div>
                ))}
                {reviews.length === 0 && <div className="text-zinc-600 text-xs">No reviews</div>}
              </div>
            </>
          ) : <div className="text-zinc-500 text-sm">Select a ticker</div>}
        </div>
      </div>
    </div>
  );
}
