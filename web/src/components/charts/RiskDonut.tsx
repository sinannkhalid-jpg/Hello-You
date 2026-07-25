"use client";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend } from "recharts";

// Status colors: only the four threat bands
const COLORS: Record<string, string> = {
  low:      "#22c55e",
  medium:   "#f59e0b",
  high:     "#f59e0b",
  critical: "#ef4444",
};

export function RiskDonut({ data }: { data: Record<string, number> }) {
  const items = Object.entries(data).map(([k, v]) => ({ name: k, value: v }));
  const total = items.reduce((s, i) => s + i.value, 0);
  if (total === 0) {
    return <div className="text-sm text-[#a1a1aa] p-6 text-center">No data yet</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={items} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} stroke="#0a0a0a" strokeWidth={2}>
          {items.map((it) => <Cell key={it.name} fill={COLORS[it.name] || "#52525b"} />)}
        </Pie>
        <Tooltip
          contentStyle={{ background: "#151515", border: "1px solid #262626", borderRadius: 8, fontSize: 12, color: "#ffffff" }}
        />
        <Legend
          iconType="circle"
          wrapperStyle={{ fontSize: 12, color: "#a1a1aa" }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
