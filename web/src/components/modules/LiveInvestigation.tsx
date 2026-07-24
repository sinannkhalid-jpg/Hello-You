"use client";
/**
 * A small "run a live investigation" panel. Streams the SSE endpoint and
 * shows progress + the final result (confidence, evidence, graph).
 */
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, RotateCcw, Download, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { InvestigationProgress } from "./InvestigationProgress";
import { useInvestigationStream } from "@/hooks/useInvestigationStream";
import { ThreatChip } from "@/components/common/ThreatChip";
import { getAccessToken } from "@/lib/api";

const KINDS = [
  { v: "domain", l: "Domain" },
  { v: "ip", l: "IP" },
  { v: "email", l: "Email" },
  { v: "username", l: "Username" },
  { v: "url", l: "URL" },
];

export function LiveInvestigation({
  initialKind = "domain",
  initialTarget = "example.com",
}: {
  initialKind?: string;
  initialTarget?: string;
}) {
  const [kind, setKind] = useState(initialKind);
  const [target, setTarget] = useState(initialTarget);
  const { events, result, streaming, error, start, cancel, reset } = useInvestigationStream();

  function run() {
    if (!target.trim() || streaming) return;
    start(kind, target.trim());
  }

  function downloadExport(fmt: "pdf" | "json" | "csv") {
    const token = getAccessToken();
    const url = `/api/v1/intel/investigate/export?kind=${kind}&target=${encodeURIComponent(target)}&fmt=${fmt}`;
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.blob())
      .then((b) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(b);
        a.download = `investigation.${fmt}`;
        a.click();
      });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-4 w-4" /> Live investigation
        </CardTitle>
        <CardDescription>Streams progress events from the backend.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-[140px,1fr,auto]">
          <div>
            <Label className="text-xs">Kind</Label>
            <Select value={kind} onValueChange={setKind}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                {KINDS.map((k) => (
                  <SelectItem key={k.v} value={k.v}>{k.l}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Target</Label>
            <Input className="mt-1" value={target} onChange={(e) => setTarget(e.target.value)} />
          </div>
          <div className="flex items-end gap-2">
            {!streaming ? (
              <Button onClick={run} disabled={!target.trim()}>
                <Play className="h-4 w-4" /> Run
              </Button>
            ) : (
              <Button variant="ghost" onClick={cancel}>
                <RotateCcw className="h-4 w-4" /> Cancel
              </Button>
            )}
          </div>
        </div>

        <InvestigationProgress events={events} result={result} streaming={streaming} />

        {error && (
          <p className="text-xs text-rose-300">{error}</p>
        )}

        <AnimatePresence>
          {result && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="rounded-md border border-white/10 bg-white/5 p-3 text-sm space-y-2"
            >
              <div className="flex items-center gap-2 flex-wrap">
                <ThreatChip level={result.summary?.risk} score={result.summary?.score} />
                <span className="text-xs text-muted-foreground">
                  confidence {(result.confidence * 100).toFixed(0)}% · {result.meta?.providers_ok}/{result.meta?.providers_queried} providers
                </span>
              </div>
              {result.evidence?.length > 0 && (
                <ul className="text-xs space-y-1">
                  {result.evidence.slice(0, 4).map((e: any) => (
                    <li key={e.id} className="flex items-center gap-2">
                      <span className={`chip chip-${e.severity}`} style={{ minWidth: 64, justifyContent: "center" }}>
                        {e.severity}
                      </span>
                      <span className="truncate">{e.title}</span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="flex items-center gap-2 pt-1">
                <Button size="sm" variant="ghost" onClick={() => downloadExport("pdf")}>
                  <Download className="h-3.5 w-3.5" /> PDF
                </Button>
                <Button size="sm" variant="ghost" onClick={() => downloadExport("json")}>
                  <Download className="h-3.5 w-3.5" /> JSON
                </Button>
                <Button size="sm" variant="ghost" onClick={() => downloadExport("csv")}>
                  <Download className="h-3.5 w-3.5" /> CSV
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}
