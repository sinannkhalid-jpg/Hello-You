import { threatChip } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { ShieldAlert } from "lucide-react";

export function ThreatChip({ level, className, score }: { level?: string | null; className?: string; score?: number | null }) {
  const label = (level || "unknown").toString();
  return (
    <span className={cn("chip", threatChip(label), className)}>
      <ShieldAlert className="h-3 w-3" />
      <span className="capitalize">{label}</span>
      {score != null && <span className="opacity-80">· {score}</span>}
    </span>
  );
}
