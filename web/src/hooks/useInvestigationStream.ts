"use client";
/**
 * Stream an investigation via Server-Sent Events.
 *
 * Returns a live list of progress events and the final result.
 * The backend sends events with `stage: "start" | "checking" | "completed"
 * | "failed" | "skipped" | "done" | "result"` plus a final result.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { getAccessToken } from "@/lib/api";

export type ProgressStage =
  | "start"
  | "checking"
  | "completed"
  | "failed"
  | "skipped"
  | "done"
  | "result";

export interface ProgressEvent {
  stage: ProgressStage;
  message: string;
  provider?: string;
  ts: number;
  meta?: Record<string, any>;
}

export function useInvestigationStream() {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [result, setResult] = useState<any>(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setEvents([]);
    setResult(null);
    setError(null);
  }, []);

  const start = useCallback(
    async (kind: string, target: string, providers?: string[]) => {
      reset();
      setStreaming(true);
      const controller = new AbortController();
      abortRef.current = controller;

      const params = new URLSearchParams({ kind, target });
      if (providers?.length) params.set("providers", providers.join(","));
      const url = `/api/v1/intel/investigate/stream?${params.toString()}`;
      const token = getAccessToken();

      try {
        const r = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: controller.signal,
        });
        if (!r.ok || !r.body) {
          throw new Error(`HTTP ${r.status}`);
        }
        const reader = r.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          // SSE events are separated by blank lines.
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() || "";
          for (const block of blocks) {
            const dataLine = block
              .split("\n")
              .find((l) => l.startsWith("data:"));
            if (!dataLine) continue;
            try {
              const payload = JSON.parse(dataLine.slice(5).trim());
              if (payload.stage === "result") {
                setResult(payload.result);
              } else {
                setEvents((prev) => [...prev, payload]);
              }
            } catch {
              /* ignore non-JSON frames */
            }
          }
        }
      } catch (e: any) {
        if (e?.name !== "AbortError") {
          setError(e?.message || "stream failed");
        }
      } finally {
        setStreaming(false);
      }
    },
    [reset],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return { events, result, streaming, error, start, cancel, reset };
}
