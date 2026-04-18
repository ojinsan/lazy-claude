"use client";

import { Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PerformanceDaily } from "@/lib/api";

function fmt(v: number) {
  return `${(v / 1_000_000).toFixed(1)}M`;
}

export function EquityCurve({ data }: { data: PerformanceDaily[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#8a8f98" }} tickLine={false} axisLine={false} />
        <YAxis tickFormatter={fmt} tick={{ fontSize: 11, fill: "#8a8f98" }} tickLine={false} axisLine={false} />
        <Tooltip
          formatter={(value) => fmt(Number(value))}
          contentStyle={{
            background: "#111318",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "12px",
            color: "#f7f8f8",
          }}
          labelStyle={{ color: "#b0b6c1" }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: "#b0b6c1" }} />
        <Line type="monotone" dataKey="equity" stroke="var(--chart-1)" dot={false} strokeWidth={2.5} name="Equity" />
        <Line type="monotone" dataKey="ihsg_close" stroke="var(--chart-3)" dot={false} strokeWidth={1.5} name="IHSG" />
      </LineChart>
    </ResponsiveContainer>
  );
}
