"use client";
/**
 * Live progress UI for an investigation. Renders the staged events from
 * the SSE stream: "Searching…", "Checking Shodan…", "Completed", etc.
 */
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, Loader2, Search, SkipForward } from "lucide-react";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { ProgressEvent } from "@/hooks/useInvestigationStream";

const STAGE_ICON: Record<string, any> = {
  start: Loader2,
  checking: Search,
  completed: CheckCircle2,
  failed: XCircle,
  skipped: SkipForward,
  done: CheckCircle2,
};

const STAGE_COLOR: Record<string, string> = {
  start: "text-[#a1a1aa]",
  checking: "text-white",
  completed: "text-[#22c55e]",
  failed: "text-[#ef4444]",
  skipped: "text-[#71717a]",
  done: "text-[#22c55e]",
};

export function InvestigationProgress({
  events,
  streaming,
}: {
  events: ProgressEvent[];
  result?: any;
  streaming: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length]);

  return (
    <div className="rounded-xl border border-[#262626] bg-[#0a0a0a] p-4 font-mono text-xs max-h-[420px] overflow-y-auto text-[#a1a1aa]">
      {events.length === 0 && streaming && (
        <p className="text-[#71717a]">Initializing…</p>
      )}
      <AnimatePresence initial={false}>
        {events.map((e, i) => {
          const Icon = STAGE_ICON[e.stage] || Search;
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.15 }}
              className="flex items-center gap-2 py-1"
            >
              <Icon
                className={cn(
                  "h-3.5 w-3.5 shrink-0",
                  STAGE_COLOR[e.stage],
                  e.stage === "checking" && "animate-pulse",
                )}
              />
              <span className={cn("truncate", STAGE_COLOR[e.stage])}>
                {e.message}
              </span>
              {typeof e.meta?.duration_ms === "number" && (
                <span className="ml-auto text-[10px] text-[#71717a]">
                  {e.meta.duration_ms}ms
                </span>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
      <div ref={bottomRef} />
    </div>
  );
}
