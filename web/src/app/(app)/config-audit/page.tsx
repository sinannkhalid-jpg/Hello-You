"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Config } from "@/lib/api";
import { ModuleShell } from "@/components/modules/ModuleShell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, KeyRound, AlertTriangle, Settings, Search } from "lucide-react";
import { cn } from "@/lib/utils";

function StatusBadge({ status }: { status: string }) {
  if (status === "registered" || status === "enabled") {
    return <Badge className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30">registered</Badge>;
  }
  if (status === "missing_key" || status === "no_api_key") {
    return <Badge className="bg-amber-500/15 text-amber-300 border-amber-500/30">missing key</Badge>;
  }
  if (status === "not_registered") {
    return <Badge className="bg-slate-500/15 text-slate-300 border-slate-500/30">not registered</Badge>;
  }
  if (status === "disabled") {
    return <Badge className="bg-slate-500/15 text-slate-300 border-slate-500/30">disabled</Badge>;
  }
  return <Badge className="bg-white/10 text-muted-foreground">{status}</Badge>;
}

export default function ConfigAuditPage() {
  const [probe, setProbe] = useState(false);
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["config-audit", probe],
    queryFn: () => Config.audit(probe),
  });

  return (
    <ModuleShell
      title="API configuration audit"
      description="List of every external API the platform can use, with required environment variables and provider status."
      icon={<Settings className="h-5 w-5" />}
      input={
        <div className="flex items-center gap-2">
          <Button onClick={() => setProbe(!probe)} variant="outline" size="sm">
            {probe ? "Without probes" : "Probe enabled providers"}
          </Button>
          <Button onClick={() => refetch()} size="sm" variant="ghost">Refresh</Button>
        </div>
      }
      run={null}
      loading={isLoading}
      error={null}
      summary={data && (
        <div className="grid gap-4 sm:grid-cols-4">
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Total APIs</p>
            <p className="mt-1 text-2xl font-semibold">{data.summary.total}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Configured</p>
            <p className="mt-1 text-2xl font-semibold text-emerald-300">{data.summary.configured}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Missing key</p>
            <p className="mt-1 text-2xl font-semibold text-amber-300">{data.summary.missing_key}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Registered</p>
            <p className="mt-1 text-2xl font-semibold text-cyan-300">{data.summary.registered}</p>
          </CardContent></Card>
        </div>
      )}
    >
      {data && (
        <div className="space-y-3">
          {data.apis.map((api: any) => (
            <Card key={api.name}>
              <CardHeader>
                <div className="flex items-start gap-3">
                  {api.configured
                    ? <CheckCircle2 className="h-5 w-5 text-emerald-300 mt-0.5" />
                    : api.required_variables && api.required_variables.length > 0
                      ? <KeyRound className="h-5 w-5 text-amber-300 mt-0.5" />
                      : <AlertTriangle className="h-5 w-5 text-muted-foreground mt-0.5" />
                  }
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-base">{api.name}</CardTitle>
                    <CardDescription className="mt-0.5">{api.purpose}</CardDescription>
                  </div>
                  <StatusBadge status={api.provider_status} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2 sm:grid-cols-2 text-sm">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Status</p>
                    <p className="mt-0.5 font-medium">{api.configured ? "Configured" : "Not configured"}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Reason</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{api.reason}</p>
                  </div>
                  {api.required_variables && api.required_variables.length > 0 && (
                    <div className="sm:col-span-2">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Required variable(s)</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {api.required_variables.map((v: string) => (
                          <code key={v}
                                className={cn(
                                  "text-[11px] px-1.5 py-0.5 rounded font-mono",
                                  api.missing_variables?.includes(v)
                                    ? "bg-amber-500/15 text-amber-300"
                                    : "bg-emerald-500/15 text-emerald-300",
                                )}>
                            {v}
                          </code>
                        ))}
                        {api.legacy_variables && api.legacy_variables.map((v: string) => (
                          <code key={v}
                                className="text-[11px] px-1.5 py-0.5 rounded font-mono bg-slate-500/15 text-slate-300">
                            {v} <span className="text-[9px] opacity-70">(legacy)</span>
                          </code>
                        ))}
                      </div>
                    </div>
                  )}
                  {api.note && (
                    <div className="sm:col-span-2">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Note</p>
                      <p className="mt-0.5 text-[11px] text-muted-foreground">{api.note}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </ModuleShell>
  );
}
