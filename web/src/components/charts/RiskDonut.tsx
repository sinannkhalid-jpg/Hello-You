"use client";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend } from "recharts";

const COLORS: Record<string, string> = {
  low: "#34d399",
  medium: "#f59e0b",
  high: "#fb923c",
  critical: "#ff4d6d",
};

export function RiskDonut({ data }: { data: Record<string, number> }) {
  const items = Object.entries(data).map(([k, v]) => ({ name: k, value: v }));
  const total = items.reduce((s, i) => s + i.value, 0);
  if (total === 0) {
    return <div className="text-sm text-muted-foreground p-6 text-center">No data yet</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={items} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} stroke="none">
          {items.map((it) => <Cell key={it.name} fill={COLORS[it.name] || "#94a3b8"} />)}
        </Pie>
        <Tooltip
          contentStyle={{ background: "rgba(15,23,42,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
        />
        <Legend
          iconType="circle"
          wrapperStyle={{ fontSize: 12, color: "#cbd5e1" }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
