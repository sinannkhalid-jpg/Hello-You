"use client";
import { motion } from "framer-motion";
import { cn, fmtNumber } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { LucideIcon, TrendingUp, TrendingDown } from "lucide-react";

export function StatCard({
  title,
  value,
  icon: Icon,
  delta,
  accent = "cyan",
  hint,
}: {
  title: string;
  value: string | number | null;
  icon: LucideIcon;
  delta?: { value: number; positive?: boolean };
  accent?: "cyan" | "violet" | "pink" | "green" | "amber" | "red";
  hint?: string;
}) {
  const accentMap: Record<string, string> = {
    cyan: "from-cyan-500/20 to-cyan-500/0 text-cyan-300",
    violet: "from-violet-500/20 to-violet-500/0 text-violet-300",
    pink: "from-fuchsia-500/20 to-fuchsia-500/0 text-fuchsia-300",
    green: "from-emerald-500/20 to-emerald-500/0 text-emerald-300",
    amber: "from-amber-500/20 to-amber-500/0 text-amber-300",
    red: "from-rose-500/20 to-rose-500/0 text-rose-300",
  };
  return (
    <motion.div whileHover={{ y: -2 }} transition={{ type: "spring", stiffness: 300, damping: 20 }}>
      <Card className="card-hover overflow-hidden relative">
        <div className={cn("absolute inset-0 bg-gradient-to-br opacity-60 pointer-events-none", accentMap[accent].split(" ").slice(0, 2).join(" "))} />
        <CardContent className="relative p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">{title}</p>
              <p className="mt-2 text-2xl font-semibold">{value == null ? "—" : fmtNumber(value as number)}</p>
              {hint && <p className="mt-1 text-xs text-muted-foreground/80">{hint}</p>}
            </div>
            <div className={cn("grid h-10 w-10 place-items-center rounded-lg bg-white/5 border border-white/10", accentMap[accent].split(" ").slice(-1))}>
              <Icon className="h-5 w-5" />
            </div>
          </div>
          {delta && (
            <div className={cn("mt-3 inline-flex items-center gap-1 text-xs", delta.positive ? "text-emerald-300" : "text-rose-300")}>
              {delta.positive ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
              <span>{delta.value > 0 ? "+" : ""}{delta.value}%</span>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
