import { Badge } from "@/components/ui/badge";

async function getTapeStates(ticker?: string) {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8787/api/v1";
  const url = new URL(`${base}/tape-states`);
  if (ticker) url.searchParams.set("ticker", ticker);
  url.searchParams.set("limit", "100");
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) return { items: [], count: 0 };
  return res.json();
}

const compositeColor = (c: string) => {
  if (c === "ideal_markup") return "text-green-400";
  if (c === "healthy_markup") return "text-emerald-400";
  if (c === "spring_ready") return "text-cyan-400";
  if (c === "fake_support" || c === "distribution_trap") return "text-red-400";
  if (c === "spam_warning") return "text-orange-400";
  return "text-zinc-400";
};

export default async function TapePage({ searchParams }: { searchParams: Promise<{ ticker?: string }> }) {
  const { ticker } = await searchParams;
  const data = await getTapeStates(ticker);

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Tape States</h1>
      <div className="text-sm text-zinc-400">Live feed from tape_runner.snapshot — updates each monitoring cycle.</div>

      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-zinc-500 border-b border-zinc-800 text-left text-xs">
            {["Time","Ticker","Composite","Confidence","Wall Fate"].map(h => <th key={h} className="py-1.5 pr-4">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.items.map((t: any) => (
            <tr key={t.id} className="border-b border-zinc-900 hover:bg-zinc-900">
              <td className="py-1.5 pr-4 text-zinc-500 text-xs">{t.ts?.slice(0, 16)}</td>
              <td className="pr-4 text-cyan-400 font-mono">{t.ticker}</td>
              <td className={`pr-4 font-semibold ${compositeColor(t.composite)}`}>{t.composite}</td>
              <td className="pr-4"><Badge variant="outline" className="text-xs">{t.confidence}</Badge></td>
              <td className="pr-4 text-zinc-400">{t.wall_fate || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.items.length === 0 && <div className="text-zinc-500 text-sm py-4">No tape states yet</div>}
    </div>
  );
}
