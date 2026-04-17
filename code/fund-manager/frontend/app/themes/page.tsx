import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export default async function Themes() {
  const data = await api.getThemes().catch(() => ({ items: [], count: 0 }));

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Themes ({data.count})</h1>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
        {data.items.map((t) => (
          <details key={t.slug} className="border border-zinc-800 rounded bg-zinc-900">
            <summary className="px-3 py-2 cursor-pointer">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-white">{t.name}</span>
                <Badge variant={t.status === "active" ? "secondary" : "outline"} className="text-xs">{t.status}</Badge>
                {t.sector && <span className="text-zinc-500 text-xs">{t.sector}</span>}
              </div>
              {t.related_tickers && (
                <div className="flex gap-1 flex-wrap mt-1">
                  {t.related_tickers.split(",").filter(Boolean).map((tk) => (
                    <Link key={tk} href={`/ticker/${tk.trim()}`} className="text-xs text-cyan-400 hover:underline" onClick={(e) => e.stopPropagation()}>{tk.trim()}</Link>
                  ))}
                </div>
              )}
            </summary>
            <div className="px-3 pb-3 pt-1 text-xs text-zinc-400 whitespace-pre-wrap border-t border-zinc-800">
              {t.body_md || "No description"}
            </div>
          </details>
        ))}
        {data.items.length === 0 && <div className="text-zinc-500 text-sm col-span-3">No themes</div>}
      </div>
    </div>
  );
}
