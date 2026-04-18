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

  const sev = (s: string) => {
    if (s === "high") return "destructive";
    if (s === "medium") return "warning";
    return "secondary";
  };

  return (
    <div className="space-y-2">
      {signals.length === 0 ? <div className="rounded-xl border border-dashed border-border/80 px-4 py-6 text-sm text-muted-foreground">No signals yet</div> : null}
      <div className="space-y-2">
        {signals.map((s) => (
          <div key={s.id} className="flex items-center gap-3 rounded-xl border border-border/70 bg-secondary/35 px-3 py-2.5 text-sm">
            <Badge variant={sev(s.severity) as "destructive" | "warning" | "secondary"} className="shrink-0 capitalize">
              {s.severity}
            </Badge>
            <span className="mono w-16 shrink-0 text-[13px] text-foreground">{s.ticker}</span>
            <span className="truncate text-muted-foreground">{s.kind}</span>
            <span className="ml-auto text-xs text-muted-foreground">{s.layer}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
