"use client";
import { BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Cell } from "recharts";

// Monochrome with subtle accent only on the leading bar
const COLORS = ["#ffffff", "#a1a1aa", "#71717a", "#52525b", "#3f3f46", "#a1a1aa", "#71717a", "#52525b", "#3f3f46", "#27272a"];

export function CountryBar({ data }: { data: Record<string, number> }) {
  const items = Object.entries(data).map(([k, v]) => ({ name: k, value: v }));
  if (items.length === 0) {
    return <div className="text-sm text-[#a1a1aa] p-6 text-center">No data yet</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={items} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#262626" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="name" tick={{ fill: "#a1a1aa", fontSize: 11 }} stroke="#262626" />
        <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} allowDecimals={false} stroke="#262626" />
        <Tooltip
          contentStyle={{ background: "#151515", border: "1px solid #262626", borderRadius: 8, fontSize: 12, color: "#ffffff" }}
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {items.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
