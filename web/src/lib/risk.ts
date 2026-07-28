/**
 * Risk Score helpers (single source of truth on the frontend).
 *
 * Risk Score = 0-100, higher = higher risk.
 *
 *   0-20   → "Low Risk"   (green  #22c55e)
 *   21-40  → "Guarded"    (lime   #84cc16)
 *   41-60  → "Moderate"   (amber  #f59e0b)
 *   61-80  → "High Risk"  (orange #f97316)
 *   81-100 → "Critical"   (red    #ef4444)
 *
 * This is the canonical, never-inverted terminology. Anywhere a
 * value is shown to the user, it must use these exact labels.
 */
export type RiskLevel =
  | "Low Risk"
  | "Guarded"
  | "Moderate"
  | "High Risk"
  | "Critical";

export type RiskToken = "low" | "guarded" | "medium" | "high" | "critical";

export interface RiskBand {
  name: RiskLevel;
  token: RiskToken;
  min: number;
  max: number;
  color: string;        // hex
  classes: string;      // Tailwind utility classes
}

export const RISK_BANDS: RiskBand[] = [
  { name: "Critical",  token: "critical", min: 81, max: 100, color: "#ef4444",
    classes: "border-[#ef4444]/30 bg-[#ef4444]/5 text-[#ef4444]" },
  { name: "High Risk", token: "high",     min: 61, max:  80, color: "#f97316",
    classes: "border-[#f97316]/30 bg-[#f97316]/5 text-[#f97316]" },
  { name: "Moderate",  token: "medium",   min: 41, max:  60, color: "#f59e0b",
    classes: "border-[#f59e0b]/30 bg-[#f59e0b]/5 text-[#f59e0b]" },
  { name: "Guarded",   token: "guarded",  min: 21, max:  40, color: "#84cc16",
    classes: "border-[#84cc16]/30 bg-[#84cc16]/5 text-[#84cc16]" },
  { name: "Low Risk",  token: "low",      min:  0, max:  20, color: "#22c55e",
    classes: "border-[#22c55e]/30 bg-[#22c55e]/5 text-[#22c55e]" },
];

// Map of any-token-or-name → canonical name.
const _LEGACY_TO_NAME: Record<string, RiskLevel> = {
  low:      "Low Risk",
  guarded:  "Guarded",
  medium:   "Moderate",
  high:     "High Risk",
  critical: "Critical",
};

const _NAME_TO_TOKEN: Record<RiskLevel, RiskToken> = {
  "Low Risk":  "low",
  "Guarded":   "guarded",
  "Moderate":  "medium",
  "High Risk": "high",
  "Critical":  "critical",
};

const _NAME_TO_COLOR: Record<RiskLevel, string> = {
  "Low Risk":  "#22c55e",
  "Guarded":   "#84cc16",
  "Moderate":  "#f59e0b",
  "High Risk": "#f97316",
  "Critical":  "#ef4444",
};

const _NAME_TO_CLASSES: Record<RiskLevel, string> = {
  "Low Risk":  "border-[#22c55e]/30 bg-[#22c55e]/5 text-[#22c55e]",
  "Guarded":   "border-[#84cc16]/30 bg-[#84cc16]/5 text-[#84cc16]",
  "Moderate":  "border-[#f59e0b]/30 bg-[#f59e0b]/5 text-[#f59e0b]",
  "High Risk": "border-[#f97316]/30 bg-[#f97316]/5 text-[#f97316]",
  "Critical":  "border-[#ef4444]/30 bg-[#ef4444]/5 text-[#ef4444]",
};

/** Normalize any of: a short token ("low"/"medium"/"high"/"critical"
 *  /"guarded"), a canonical name, or a legacy "threat_level" value
 *  to a canonical RiskLevel. Unknown / null → "Moderate" (safe). */
export function normalizeRiskLevel(input: string | null | undefined): RiskLevel {
  if (!input) return "Moderate";
  const k = String(input).trim().toLowerCase();
  if (k in _LEGACY_TO_NAME) return _LEGACY_TO_NAME[k];
  for (const lvl of RISK_BANDS) {
    if (lvl.name.toLowerCase() === k) return lvl.name;
  }
  return "Moderate";
}

/** Classify a numeric 0-100 score into a band. */
export function classifyRisk(score: number | null | undefined): RiskBand {
  if (score == null) return RISK_BANDS[RISK_BANDS.length - 1]; // Low Risk
  const s = Math.max(0, Math.min(100, Math.round(Number(score))));
  for (const b of RISK_BANDS) {
    if (s >= b.min && s <= b.max) return b;
  }
  return RISK_BANDS[RISK_BANDS.length - 1];
}

/** Return the Tailwind class set for a given level / token. */
export function classesForRisk(level: string | null | undefined): string {
  const name = normalizeRiskLevel(level);
  return _NAME_TO_CLASSES[name];
}

/** Return the hex color for a given level / token. */
export function colorForRisk(level: string | null | undefined): string {
  return _NAME_TO_COLOR[normalizeRiskLevel(level)];
}

/** Return the short token for a given canonical name. */
export function tokenForRisk(level: string | null | undefined): RiskToken {
  return _NAME_TO_TOKEN[normalizeRiskLevel(level)];
}

/** Map a band to the chip CSS class (kept for back-compat with
 *  existing `threatChip` callsites that take a string). */
export function riskChipClass(level: string | null | undefined): string {
  return classesForRisk(level);
}
