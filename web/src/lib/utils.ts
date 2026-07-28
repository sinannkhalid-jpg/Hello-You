import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtNumber(n: number | null | undefined) {
  if (n == null) return "—";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "k";
  return String(n);
}

export function fmtDate(iso: string | Date | null | undefined, withTime = true) {
  if (!iso) return "—";
  const d = typeof iso === "string" ? new Date(iso) : iso;
  if (isNaN(d.getTime())) return "—";
  const date = d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
  if (!withTime) return date;
  const time = d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  return `${date} · ${time}`;
}

export function fmtRelative(iso: string | Date | null | undefined) {
  if (!iso) return "—";
  const d = typeof iso === "string" ? new Date(iso) : iso;
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return fmtDate(d, false);
}

export function threatChip(level?: string | null) {
  // Back-compat alias: maps any of {short token, canonical name,
  // legacy "threat_level" value} to the chip class for that band.
  // Prefer `RiskChip` directly in new code.
  switch ((level || "").toLowerCase()) {
    case "low":
    case "low risk":      return "chip-low";
    case "guarded":       return "chip-guarded";
    case "medium":
    case "moderate":      return "chip-medium";
    case "high":
    case "high risk":     return "chip-high";
    case "critical":      return "chip-critical";
    default:              return "chip-unknown";
  }
}

export function debounce<T extends (...a: any[]) => void>(fn: T, ms = 250) {
  let t: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (t) clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

export function isValidEmail(v: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
}
export function isValidDomain(v: string) {
  return /^([a-z0-9-]+\.)+[a-z]{2,}$/i.test(v.trim());
}
export function isValidIp(v: string) {
  return /^(\d{1,3}\.){3}\d{1,3}$/.test(v.trim());
}
