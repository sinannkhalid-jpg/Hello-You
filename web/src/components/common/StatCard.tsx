"use client";
import { cn, fmtNumber } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { LucideIcon, TrendingUp, TrendingDown } from "lucide-react";

export function StatCard({
  title,
  value,
  icon: Icon,
  delta,
  hint,
}: {
  title: string;
  value: string | number | null;
  icon: LucideIcon;
  delta?: { value: number; positive?: boolean };
  hint?: string;
}) {
  return (
    <Card className="card-hover overflow-hidden relative">
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wider text-[#a1a1aa]">{title}</p>
            <p className="mt-2 text-2xl font-semibold">{value == null ? "—" : fmtNumber(value as number)}</p>
            {hint && <p className="mt-1 text-xs text-[#71717a]">{hint}</p>}
          </div>
          <div className="grid h-10 w-10 place-items-center rounded-md bg-[#1a1a1a] border border-[#262626] text-white">
            <Icon className="h-5 w-5" />
          </div>
        </div>
        {delta && (
          <div className={cn("mt-3 inline-flex items-center gap-1 text-xs", delta.positive ? "text-[#22c55e]" : "text-[#ef4444]")}>
            {delta.positive ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
            <span>{delta.value > 0 ? "+" : ""}{delta.value}%</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
