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
    return <Badge className="bg-[#22c55e]/10 text-[#22c55e] border-[#22c55e]/30">registered</Badge>;
  }
  if (status === "missing_key" || status === "no_api_key") {
    return <Badge className="bg-[#f59e0b]/10 text-[#f59e0b] border-[#f59e0b]/30">missing key</Badge>;
  }
  if (status === "not_registered") {
    return <Badge className="bg-[#1a1a1a] text-[#a1a1aa] border-[#262626]">not registered</Badge>;
  }
  if (status === "disabled") {
    return <Badge className="bg-[#1a1a1a] text-[#a1a1aa] border-[#262626]">disabled</Badge>;
  }
  return <Badge className="bg-[#1a1a1a] text-[#a1a1aa] border-[#262626]">{status}</Badge>;
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
          <Button onClick={() => setProbe(!probe)} variant="secondary" size="sm">
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
            <p className="text-xs uppercase tracking-wider text-[#a1a1aa]">Total APIs</p>
            <p className="mt-1 text-2xl font-semibold">{data.summary.total}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-[#a1a1aa]">Configured</p>
            <p className="mt-1 text-2xl font-semibold text-white">{data.summary.configured}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-[#a1a1aa]">Missing key</p>
            <p className="mt-1 text-2xl font-semibold text-[#f59e0b]">{data.summary.missing_key}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-[#a1a1aa]">Registered</p>
            <p className="mt-1 text-2xl font-semibold text-white">{data.summary.registered}</p>
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
                    ? <CheckCircle2 className="h-5 w-5 text-[#22c55e] mt-0.5" />
                    : api.required_variables && api.required_variables.length > 0
                      ? <KeyRound className="h-5 w-5 text-[#f59e0b] mt-0.5" />
                      : <AlertTriangle className="h-5 w-5 text-[#a1a1aa] mt-0.5" />
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
                    <p className="text-[10px] uppercase tracking-wider text-[#a1a1aa]">Status</p>
                    <p className="mt-0.5 font-medium">{api.configured ? "Configured" : "Not configured"}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-[#a1a1aa]">Reason</p>
                    <p className="mt-0.5 text-xs text-[#a1a1aa]">{api.reason}</p>
                  </div>
                  {api.required_variables && api.required_variables.length > 0 && (
                    <div className="sm:col-span-2">
                      <p className="text-[10px] uppercase tracking-wider text-[#a1a1aa]">Required variable(s)</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {api.required_variables.map((v: string) => (
                          <code key={v}
                                className={cn(
                                  "text-[11px] px-1.5 py-0.5 rounded font-mono",
                                  api.missing_variables?.includes(v)
                                    ? "bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/30"
                                    : "bg-[#22c55e]/10 text-[#22c55e] border border-[#22c55e]/30",
                                )}>
                            {v}
                          </code>
                        ))}
                        {api.legacy_variables && api.legacy_variables.map((v: string) => (
                          <code key={v}
                                className="text-[11px] px-1.5 py-0.5 rounded font-mono bg-[#1a1a1a] text-[#a1a1aa] border border-[#262626]">
                            {v} <span className="text-[9px] opacity-70">(legacy)</span>
                          </code>
                        ))}
                      </div>
                    </div>
                  )}
                  {api.note && (
                    <div className="sm:col-span-2">
                      <p className="text-[10px] uppercase tracking-wider text-[#a1a1aa]">Note</p>
                      <p className="mt-0.5 text-[11px] text-[#a1a1aa]">{api.note}</p>
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
