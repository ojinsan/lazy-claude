import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function KpiCard({ title, value, sub, className }: { title: string; value: string | number; sub?: string; className?: string }) {
  return (
    <Card className={`bg-zinc-900 border-zinc-800 ${className ?? ""}`}>
      <CardHeader className="pb-1">
        <CardTitle className="text-xs text-zinc-400 font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-white">{value}</div>
        {sub && <div className="text-xs text-zinc-500 mt-0.5">{sub}</div>}
      </CardContent>
    </Card>
  );
}
