"use client";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { Signal } from "@/lib/api";

export function SignalsFeed({ initial }: { initial: Signal[] }) {
  const [signals, setSignals] = useState<Signal[]>(initial);

  useEffect(() => {
    const es = new EventSource("/api/v1/signals/stream");
    es.onmessage = (e) => {
      try {
        const sig = JSON.parse(e.data) as Signal;
        setSignals((prev) => [sig, ...prev].slice(0, 20));
      } catch {}
    };
    return () => es.close();
  }, []);

  const sev = (s: string) => s === "high" ? "destructive" : s === "medium" ? "secondary" : "outline";

  return (
    <div className="space-y-1 max-h-80 overflow-y-auto">
      {signals.length === 0 && <div className="text-zinc-500 text-sm">No signals yet</div>}
      {signals.map((s) => (
        <div key={s.id} className="flex items-center gap-2 text-xs py-1 border-b border-zinc-800">
          <Badge variant={sev(s.severity) as "destructive" | "secondary" | "outline"} className="shrink-0">{s.severity}</Badge>
          <span className="font-mono text-zinc-300 w-16 shrink-0">{s.ticker}</span>
          <span className="text-zinc-400">{s.kind}</span>
          <span className="text-zinc-600 ml-auto">{s.layer}</span>
        </div>
      ))}
    </div>
  );
}
