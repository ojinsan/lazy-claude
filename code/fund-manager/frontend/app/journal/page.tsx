import { api } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export default async function Journal() {
  const today = new Date().toISOString().slice(0, 10);
  const [layersResp, lessonsResp] = await Promise.allSettled([
    api.getLayerOutputs(today),
    api.getLessons(undefined, undefined, undefined, 30),
  ]);

  const layers = layersResp.status === "fulfilled" ? layersResp.value.items : [];
  const lessons = lessonsResp.status === "fulfilled" ? lessonsResp.value.items : [];

  const grouped: Record<string, typeof layers> = {};
  layers.forEach((lo) => {
    grouped[lo.layer] = [...(grouped[lo.layer] || []), lo];
  });

  const sevBadge = (s: string) => s === "high" ? "destructive" : s === "medium" ? "secondary" : "outline";

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Journal</h1>
      <Tabs defaultValue="daily">
        <TabsList className="bg-zinc-900">
          <TabsTrigger value="daily">Daily</TabsTrigger>
          <TabsTrigger value="lessons">Lessons ({lessons.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="daily">
          <div className="text-sm text-zinc-400 mb-3">{today}</div>
          {Object.entries(grouped).map(([layer, items]) => (
            <details key={layer} open className="mb-3 border border-zinc-800 rounded">
              <summary className="px-3 py-2 cursor-pointer text-sm font-semibold bg-zinc-900 flex items-center gap-2">
                <Badge variant="outline">{layer}</Badge>
                <span>{items.length} entries</span>
              </summary>
              <div className="divide-y divide-zinc-900">
                {items.map((lo) => (
                  <div key={lo.id} className="px-3 py-2 text-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-zinc-500 text-xs">{lo.ts?.slice(11, 16)}</span>
                      {lo.severity && <Badge variant={sevBadge(lo.severity) as "destructive"|"secondary"|"outline"} className="text-xs">{lo.severity}</Badge>}
                    </div>
                    <div className="text-zinc-300">{lo.summary}</div>
                    {lo.body_md && <details className="mt-1"><summary className="text-zinc-600 text-xs cursor-pointer">expand</summary><pre className="text-zinc-400 text-xs mt-1 whitespace-pre-wrap">{lo.body_md}</pre></details>}
                  </div>
                ))}
              </div>
            </details>
          ))}
          {layers.length === 0 && <div className="text-zinc-500 text-sm py-4">No layer outputs today</div>}
        </TabsContent>

        <TabsContent value="lessons">
          <div className="space-y-2">
            {lessons.map((l) => (
              <div key={l.id} className="border border-zinc-800 rounded p-3 bg-zinc-900">
                <div className="flex items-center gap-2 mb-1 text-xs">
                  <Badge variant={sevBadge(l.severity) as "destructive"|"secondary"|"outline"}>{l.severity}</Badge>
                  <span className="text-zinc-400">{l.category}</span>
                  {l.pattern_tag && <span className="text-zinc-600">#{l.pattern_tag}</span>}
                  <span className="text-zinc-600 ml-auto">{l.date}</span>
                </div>
                <div className="text-sm text-zinc-200">{l.lesson_text}</div>
                {l.tickers && <div className="text-xs text-cyan-400 mt-1">{l.tickers.split(",").map((t) => <Link key={t} href={`/ticker/${t}`} className="mr-1 hover:underline">{t}</Link>)}</div>}
              </div>
            ))}
            {lessons.length === 0 && <div className="text-zinc-500 text-sm py-4">No lessons in last 30 days</div>}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
