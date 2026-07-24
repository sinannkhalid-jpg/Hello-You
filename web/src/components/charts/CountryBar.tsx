"use client";
import { BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Cell } from "recharts";

const COLORS = ["#00f0ff", "#8b5cf6", "#ff2bd6", "#34d399", "#f59e0b", "#fb923c", "#ff4d6d", "#60a5fa", "#a78bfa", "#f472b6"];

export function CountryBar({ data }: { data: Record<string, number> }) {
  const items = Object.entries(data).map(([k, v]) => ({ name: k, value: v }));
  if (items.length === 0) {
    return <div className="text-sm text-muted-foreground p-6 text-center">No data yet</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={items} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
        <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} allowDecimals={false} />
        <Tooltip
          contentStyle={{ background: "rgba(15,23,42,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
          {items.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
