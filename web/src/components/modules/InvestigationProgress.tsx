"use client";
/**
 * Live progress UI for an investigation. Renders the staged events from
 * the SSE stream: "Searching…", "Checking Shodan…", "Completed", etc.
 *
 * Optional usage:
 *   const { events, result, streaming, start } = useInvestigationStream();
 *   start("domain", "example.com");
 *   <InvestigationProgress events={events} result={result} streaming={streaming} />
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
  start: "text-cyan-300",
  checking: "text-cyan-300",
  completed: "text-emerald-300",
  failed: "text-rose-300",
  skipped: "text-muted-foreground",
  done: "text-emerald-300",
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
    <div className="rounded-xl border border-white/10 bg-black/30 p-4 font-mono text-xs max-h-[420px] overflow-y-auto">
      {events.length === 0 && streaming && (
        <p className="text-muted-foreground">Initializing…</p>
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
                <span className="ml-auto text-[10px] text-muted-foreground">
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
