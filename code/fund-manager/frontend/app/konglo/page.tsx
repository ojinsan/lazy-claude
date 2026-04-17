import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import * as fs from "fs";
import * as path from "path";

type KongloGroup = { id: string; name: string; owner: string; market_power: string; sectors: string; };
type KongloStock = { ticker: string; category: string; notes?: string; };

function loadKongloData(): { conglomerates: Array<{ id: string; name: string; owner: string; market_power: string; sectors: string[]; stocks: KongloStock[] }> } | null {
  const jsonPath = "/home/lazywork/workspace/tools/trader/data/konglo_list.json";
  try {
    return JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
  } catch { return null; }
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

  const powerColor = (p: string) => p === "high" ? "text-green-400" : p === "med" ? "text-yellow-400" : "text-zinc-400";

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Konglo Groups</h1>
      <div className="text-sm text-zinc-400">{groups.length} conglomerate groups · {groups.reduce((n, g) => n + g.stocks.length, 0)} tickers total</div>

      <div className="space-y-3">
        {groups.map((g) => (
          <details key={g.id} className="border border-zinc-800 rounded bg-zinc-900">
            <summary className="px-3 py-2 cursor-pointer">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="font-semibold text-sm text-white">{g.name}</span>
                <Badge variant="outline" className="text-xs">{g.owner}</Badge>
                <span className={`text-xs ${powerColor(g.market_power)}`}>{g.market_power}</span>
                <div className="flex gap-1 flex-wrap ml-auto">
                  {g.stocks.map((s) => (
                    <Link key={s.ticker} href={`/ticker/${s.ticker}`}
                      className="text-xs text-cyan-400 hover:underline bg-zinc-800 px-1.5 py-0.5 rounded"
                      onClick={(e) => e.stopPropagation()}>
                      {s.ticker}
                    </Link>
                  ))}
                </div>
              </div>
            </summary>
            <div className="px-3 pb-3 pt-1 border-t border-zinc-800">
              <div className="text-xs text-zinc-500 mb-1">Sectors: {g.sectors.join(", ")}</div>
              <div className="grid md:grid-cols-3 gap-2">
                {g.stocks.map((s) => (
                  <div key={s.ticker} className="text-xs text-zinc-400 flex gap-1">
                    <Link href={`/ticker/${s.ticker}`} className="text-cyan-400 hover:underline w-12 shrink-0">{s.ticker}</Link>
                    <span>{s.category}</span>
                    {s.notes && <span className="text-zinc-600">· {s.notes}</span>}
                  </div>
                ))}
              </div>
            </div>
          </details>
        ))}
      </div>

      {groups.length === 0 && <div className="text-zinc-500 text-sm py-4">Loading from konglo_list.json — {dbGroups.count} groups in DB</div>}
    </div>
  );
}
