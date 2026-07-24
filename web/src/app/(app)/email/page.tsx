"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTargetParam } from "@/hooks/useDebouncedValue";
import { Osint } from "@/lib/api";
import { ModuleShell } from "@/components/modules/ModuleShell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Mail, Search, ShieldCheck, ShieldAlert, Server } from "lucide-react";
import { ThreatChip } from "@/components/common/ThreatChip";
import { KeyValue } from "@/components/modules/KeyValueGrid";
import { RiskGauge } from "@/components/charts/RiskGauge";
import { fmtDate, isValidEmail } from "@/lib/utils";

export default function EmailPage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["email", submitted],
    queryFn: () => Osint.email(submitted!),
    enabled: !!submitted,
  });

  function run() {
    const v = target.trim();
    if (!v || !isValidEmail(v)) return;
    setSubmitted(v);
  }

  const mx = data?.mx_records ?? [];
  const hasSpf = !!data?.spf;
  const hasDkim = !!data?.dkim;
  const hasDmarc = !!data?.dmarc;
  const breaches = data?.breach_exposure;
  const gravatar = data?.gravatar_url;

  return (
    <ModuleShell
      title="Email Investigation"
      description="DNS records, email authentication, Gravatar, breach exposure."
      icon={<Mail className="h-5 w-5" />}
      input={
        <div>
          <Label htmlFor="e">Email</Label>
          <div className="relative mt-1.5">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input id="e" type="email" value={target} onChange={(e) => setTarget(e.target.value)}
                   onKeyDown={(e) => e.key === "Enter" && run()}
                   placeholder="name@example.com" className="pl-9" autoFocus />
          </div>
        </div>
      }
      run={<Button onClick={run} disabled={!isValidEmail(target) || isFetching}>
        {isFetching ? "Investigating…" : "Investigate"}
      </Button>}
      loading={isLoading} error={error}
      summary={data && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Risk score</CardTitle>
              <CardDescription>Composite signal from DNS, SPF, DKIM, DMARC, breach.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center">
              <RiskGauge value={data.risk_score || 0} label="Risk" />
              <div className="mt-2"><ThreatChip level={data.threat_level} score={data.risk_score} /></div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <KeyValue
                columns={2}
                items={[
                  { label: "Email", value: data.email, mono: true },
                  { label: "Domain", value: data.domain, mono: true },
                  { label: "Gravatar", value: gravatar ? <a className="text-cyan-300 underline" href={gravatar} target="_blank" rel="noreferrer">view</a> : "not found" },
                  { label: "Breach exposure", value: breaches ? `${breaches.length || "—"} record(s)` : "no data (set HIBP_API_KEY)" },
                ]}
              />
              <div className="mt-4 grid grid-cols-3 gap-3">
                <AuthChip label="SPF" ok={hasSpf} />
                <AuthChip label="DKIM" ok={hasDkim} />
                <AuthChip label="DMARC" ok={hasDmarc} />
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    >
      {data && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>MX records</CardTitle>
              <CardDescription>Mail routing.</CardDescription>
            </CardHeader>
            <CardContent>
              {mx.length === 0 ? <p className="text-sm text-muted-foreground">No MX records found.</p> : (
                <ul className="space-y-2 text-sm">
                  {mx.map((m: any, i: number) => (
                    <li key={i} className="flex items-center gap-2">
                      <Server className="h-3.5 w-3.5 text-cyan-300" />
                      <span className="font-mono text-xs">priority {m.priority}</span>
                      <span className="font-mono">{m.host}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Email authentication</CardTitle>
              <CardDescription>SPF / DKIM / DMARC presence.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <AuthRow label="SPF" record={data.spf} />
              <AuthRow label="DKIM" record={data.dkim} />
              <AuthRow label="DMARC" record={data.dmarc} />
            </CardContent>
          </Card>
        </div>
      )}
    </ModuleShell>
  );
}

function AuthChip({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className={`rounded-md border p-3 text-center ${ok ? "border-emerald-500/30 bg-emerald-500/10" : "border-rose-500/30 bg-rose-500/10"}`}>
      <div className="flex items-center justify-center gap-1.5 text-xs font-medium">
        {ok ? <ShieldCheck className="h-3.5 w-3.5 text-emerald-300" /> : <ShieldAlert className="h-3.5 w-3.5 text-rose-300" />}
        <span className={ok ? "text-emerald-300" : "text-rose-300"}>{label}</span>
      </div>
      <p className="text-[10px] text-muted-foreground mt-1">{ok ? "configured" : "missing"}</p>
    </div>
  );
}

function AuthRow({ label, record }: { label: string; record?: string | null }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="font-mono text-xs mt-0.5 break-all">{record || "— not published —"}</p>
    </div>
  );
}
