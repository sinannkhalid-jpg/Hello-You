"use client";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";

export function ThreatTrendChart({ data }: { data: { date: string; count: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="ct" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ffffff" stopOpacity={0.18} />
            <stop offset="100%" stopColor="#ffffff" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#262626" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: "#a1a1aa", fontSize: 11 }} tickFormatter={(d) => d.slice(5)} stroke="#262626" />
        <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} allowDecimals={false} stroke="#262626" />
        <Tooltip
          contentStyle={{
            background: "#151515",
            border: "1px solid #262626",
            borderRadius: 8,
            fontSize: 12,
            color: "#ffffff",
          }}
        />
        <Area type="monotone" dataKey="count" stroke="#ffffff" strokeWidth={2} fill="url(#ct)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
