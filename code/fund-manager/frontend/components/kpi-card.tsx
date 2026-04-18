import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function KpiCard({
  title,
  value,
  sub,
  className,
}: {
  title: string;
  value: string | number;
  sub?: string;
  className?: string;
}) {
  return (
    <Card className={cn("bg-card/85", className)}>
      <CardHeader className="gap-2 pb-0">
        <CardTitle className="section-label text-[11px]">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="text-3xl font-semibold tracking-[-0.03em] text-foreground">{value}</div>
        {sub ? <div className="text-sm text-muted-foreground">{sub}</div> : null}
      </CardContent>
    </Card>
  );
}
