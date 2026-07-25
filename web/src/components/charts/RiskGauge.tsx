"use client";
import { useEffect, useState } from "react";

export function RiskGauge({ value = 0, label = "Risk" }: { value?: number; label?: string }) {
  const [v, setV] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setV(Math.max(0, Math.min(100, value))), 60);
    return () => clearTimeout(t);
  }, [value]);

  // Color only on the gauge fill: white (low) -> amber -> red (critical)
  const angle = (v / 100) * 180;
  const color = v >= 75 ? "#ef4444" : v >= 50 ? "#f59e0b" : v >= 25 ? "#a1a1aa" : "#ffffff";

  const r = 70;
  const cx = 90, cy = 90;
  const start = polar(cx, cy, r, 180);
  const end = polar(cx, cy, r, 180 - angle);
  const large = angle > 180 ? 1 : 0;
  const filled = `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`;

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 180 110" className="w-full max-w-[220px]">
        <path
          d={polarArc(cx, cy, r, 180, 0)}
          stroke="#262626"
          strokeWidth={12}
          fill="none"
          strokeLinecap="round"
        />
        <path
          d={filled}
          stroke={color}
          strokeWidth={12}
          fill="none"
          strokeLinecap="round"
        />
        <text x="90" y="80" textAnchor="middle" fill="#ffffff" fontSize="28" fontWeight="600">
          {Math.round(v)}
        </text>
        <text x="90" y="100" textAnchor="middle" fill="#a1a1aa" fontSize="11">
          {label}
        </text>
      </svg>
    </div>
  );
}

function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
}
function polarArc(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const s = polar(cx, cy, r, startDeg);
  const e = polar(cx, cy, r, endDeg);
  const large = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
}
