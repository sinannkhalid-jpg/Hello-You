"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTargetParam } from "@/hooks/useDebouncedValue";
import { Osint } from "@/lib/api";
import { ModuleShell } from "@/components/modules/ModuleShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Network, Search } from "lucide-react";
import { KeyValue } from "@/components/modules/KeyValueGrid";
import { CodeBlock } from "@/components/modules/KeyValueGrid";
import { isValidDomain } from "@/lib/utils";

export default function DnsPage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["dns", submitted],
    queryFn: () => Osint.dns(submitted!),
    enabled: !!submitted,
  });

  function run() {
    const v = target.trim().toLowerCase();
    if (!v || !isValidDomain(v)) return;
    setSubmitted(v);
  }

  return (
    <ModuleShell
      title="DNS Lookup"
      description="A / AAAA / MX / NS / TXT / SOA / CAA / PTR / DNSSEC."
      icon={<Network className="h-5 w-5" />}
      input={
        <div>
          <Label htmlFor="d">Domain</Label>
          <div className="relative mt-1.5">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input id="d" value={target} onChange={(e) => setTarget(e.target.value)}
                   onKeyDown={(e) => e.key === "Enter" && run()}
                   placeholder="example.com" className="pl-9" autoFocus />
          </div>
        </div>
      }
      run={<Button onClick={run} disabled={!isValidDomain(target) || isFetching}>
        {isFetching ? "Resolving…" : "Resolve"}
      </Button>}
      loading={isLoading} error={error}
    >
      {data && (
        <Card>
          <CardHeader><CardTitle>Records</CardTitle></CardHeader>
          <CardContent className="space-y-5">
            <KeyValue columns={2} items={[
              { label: "A", value: (data.a || []).join("\n") || "—", mono: true },
              { label: "AAAA", value: (data.aaaa || []).join("\n") || "—", mono: true },
              { label: "NS", value: (data.ns || []).join("\n") || "—", mono: true },
              { label: "MX", value: (data.mx || []).map((m: any) => `${m.priority} ${m.host}`).join("\n") || "—", mono: true },
              { label: "TXT", value: (data.txt || []).join("\n") || "—", mono: true },
              { label: "CAA", value: (data.caa || []).map((c: any) => `${c.flag} ${c.tag} ${c.value}`).join("\n") || "—", mono: true },
              { label: "PTR", value: (data.ptr || []).join("\n") || "—", mono: true },
              { label: "DNSSEC", value: data.dnssec ? "enabled" : "not enabled" },
            ]} />
            {data.soa && <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">SOA</p>
              <CodeBlock value={data.soa} />
            </div>}
          </CardContent>
        </Card>
      )}
    </ModuleShell>
  );
}
