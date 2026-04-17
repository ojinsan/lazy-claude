import { Badge } from "@/components/ui/badge";
import Link from "next/link";

async function getConfluence() {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8787/api/v1";
  const res = await fetch(`${base}/confluence/latest`, { cache: "no-store" });
  if (!res.ok) return { items: [], count: 0 };
  return res.json();
}

const bucketColor = (b: string) => {
  if (b === "execute") return "text-green-400";
  if (b === "plan") return "text-cyan-400";
  if (b === "watch") return "text-yellow-400";
  return "text-zinc-500";
};

export default async function ConfluencePage() {
  const data = await getConfluence();

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Confluence Scores</h1>
      <div className="text-sm text-zinc-400">Latest score per ticker. Recomputed each L3 cycle.</div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
        {data.items.map((c: any) => {
          let comps: Record<string, number> = {};
          try { comps = JSON.parse(c.components_json); } catch {}
          return (
            <div key={c.id} className="border border-zinc-800 rounded bg-zinc-900 p-3">
              <div className="flex items-center justify-between mb-2">
                <Link href={`/ticker/${c.ticker}`} className="text-cyan-400 hover:underline font-bold">{c.ticker}</Link>
                <div className="flex items-center gap-2">
                  <span className={`text-2xl font-bold ${bucketColor(c.bucket)}`}>{c.score}</span>
                  <Badge variant="outline" className={`text-xs ${bucketColor(c.bucket)}`}>{c.bucket}</Badge>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-x-2 text-xs text-zinc-400">
                {Object.entries(comps).map(([k, v]) => (
                  <div key={k} className="flex justify-between py-0.5 border-b border-zinc-800">
                    <span>{k}</span>
                    <span className={Number(v) >= 0 ? "text-green-400" : "text-red-400"}>{Number(v) > 0 ? "+" : ""}{v}</span>
                  </div>
                ))}
              </div>
              <div className="text-xs text-zinc-600 mt-1">{c.ts?.slice(0, 16)}</div>
            </div>
          );
        })}
        {data.items.length === 0 && <div className="text-zinc-500 text-sm col-span-3 py-4">No scores yet</div>}
      </div>
    </div>
  );
}
