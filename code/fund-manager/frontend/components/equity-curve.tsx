"use client";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { PerformanceDaily } from "@/lib/api";

export function EquityCurve({ data }: { data: PerformanceDaily[] }) {
  const fmt = (v: number) => `${(v / 1_000_000).toFixed(1)}M`;
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#888" }} tickLine={false} />
        <YAxis tickFormatter={fmt} tick={{ fontSize: 10, fill: "#888" }} tickLine={false} axisLine={false} />
        <Tooltip formatter={(v) => fmt(Number(v))} contentStyle={{ background: "#1c1c1c", border: "1px solid #333" }} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Line type="monotone" dataKey="equity" stroke="#22d3ee" dot={false} strokeWidth={2} name="Equity" />
        <Line type="monotone" dataKey="ihsg_close" stroke="#f97316" dot={false} strokeWidth={1} name="IHSG" />
      </LineChart>
    </ResponsiveContainer>
  );
}
