"use client";
/**
 * RiskChip — the canonical badge for risk score bands.
 *
 *   risk_level  →  band name
 *   "Low Risk"    (green)
 *   "Guarded"     (lime)
 *   "Moderate"    (amber)
 *   "High Risk"   (orange)
 *   "Critical"    (red)
 *
 * Always interpret the value as RISK (higher = more risky), never as
 * reputation. The chip is the only place where the color is decided.
 */
import { ShieldAlert } from "lucide-react";
import { classesForRisk, normalizeRiskLevel } from "@/lib/risk";
import { cn } from "@/lib/utils";

export function RiskChip({
  level,
  score,
  className,
  showScore = true,
  format = "Risk: {level} ({score})",
}: {
  level?: string | null;
  score?: number | null;
  className?: string;
  showScore?: boolean;
  format?: "Risk: {level} ({score})" | "{level} · {score}" | "{level}";
}) {
  const name = normalizeRiskLevel(level);
  const scoreText = score != null ? `(${score})` : "";
  let body: string;
  if (format === "Risk: {level} ({score})") {
    body = `Risk: ${name}${score != null ? ` (${score})` : ""}`;
  } else if (format === "{level} · {score}") {
    body = `${name}${score != null ? ` · ${score}` : ""}`;
  } else {
    body = name;
  }
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border",
        classesForRisk(level),
        className,
      )}
      title={`Risk Score: ${score != null ? `${score}/100` : "—"} — ${name}`}
    >
      <ShieldAlert className="h-3 w-3" />
      <span>{body}</span>
    </span>
  );
}
