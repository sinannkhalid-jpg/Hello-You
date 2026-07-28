"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Reports } from "@/lib/api";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { FileText, Sparkles, Download } from "lucide-react";
import { CodeBlock } from "@/components/modules/KeyValueGrid";
import { RiskChip } from "@/components/common/RiskChip";
import { toast } from "sonner";

const KINDS = ["domain", "ip", "email", "username", "phone"] as const;

export default function ReportPage() {
  const [target, setTarget] = useState("");
  const [kind, setKind] = useState<typeof KINDS[number]>("domain");
  const [context, setContext] = useState("");

  const m = useMutation({
    mutationFn: () => {
      let parsed: any = {};
      try { parsed = context.trim() ? JSON.parse(context) : {}; } catch { throw new Error("Context must be valid JSON"); }
      return Reports.generate({ target, kind, context: parsed });
    },
    onError: (e: any) => toast.error(e?.message || "Failed to generate"),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Investigation Report"
        description="Generate a structured, executive-ready OSINT report."
        icon={<FileText className="h-5 w-5" />}
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Inputs</CardTitle>
            <CardDescription>Paste a result object from any investigation, or pass context in JSON.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label>Kind</Label>
              <Select value={kind} onValueChange={(v: string) => setKind(v as (typeof KINDS)[number])}>
                <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {KINDS.map((k) => <SelectItem key={k} value={k}>{k}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Target</Label>
              <Input className="mt-1.5" value={target} onChange={(e) => setTarget(e.target.value)} placeholder="example.com" />
            </div>
            <div>
              <Label>Context (JSON)</Label>
              <Textarea
                value={context}
                onChange={(e) => setContext(e.target.value)}
                rows={10}
                className="mt-1.5 font-mono text-xs"
                placeholder='{ "dns": {…}, "ssl": {…} }'
              />
            </div>
            <Button onClick={() => m.mutate()} disabled={!target || m.isPending}>
              <Sparkles className="h-4 w-4" /> {m.isPending ? "Generating…" : "Generate report"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Result</CardTitle>
            <CardDescription>Structured report.</CardDescription>
          </CardHeader>
          <CardContent>
            {m.data ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 flex-wrap">
                  <RiskChip level={m.data.risk_level ?? m.data.threat_level} score={m.data.risk_score} format="Risk: {level} ({score})" />
                  <span className="text-sm text-muted-foreground">{m.data.target}</span>
                </div>
                <div>
                  <h4 className="text-sm font-semibold">Executive summary</h4>
                  <p className="text-sm text-muted-foreground mt-1">{m.data.executive_summary}</p>
                </div>
                <div>
                  <h4 className="text-sm font-semibold">Risk assessment</h4>
                  <p className="text-sm text-muted-foreground mt-1">{m.data.risk_assessment}</p>
                </div>
                {m.data.findings?.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold">Findings</h4>
                    <ul className="mt-1 space-y-1 text-sm text-muted-foreground list-disc pl-5">
                      {m.data.findings.map((f: string, i: number) => <li key={i}>{f}</li>)}
                    </ul>
                  </div>
                )}
                {m.data.recommendations?.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold">Recommendations</h4>
                    <ul className="mt-1 space-y-1 text-sm text-muted-foreground list-disc pl-5">
                      {m.data.recommendations.map((r: string, i: number) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}
                {m.data.mitre_attack?.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold">MITRE ATT&CK</h4>
                    <ul className="mt-1 space-y-1 text-sm text-muted-foreground list-disc pl-5">
                      {m.data.mitre_attack.map((m: any, i: number) => (
                        <li key={i}><b>{m.id}</b> — {m.name} <span className="opacity-70">({m.tactic})</span></li>
                      ))}
                    </ul>
                  </div>
                )}
                <CodeBlock value={m.data} />
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Run a report to see results.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
