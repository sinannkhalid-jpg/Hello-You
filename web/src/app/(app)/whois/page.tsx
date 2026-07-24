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
import { FileBadge, Search } from "lucide-react";
import { KeyValue } from "@/components/modules/KeyValueGrid";
import { fmtDate, isValidDomain } from "@/lib/utils";

export default function WhoisPage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["whois", submitted],
    queryFn: () => Osint.whois(submitted!),
    enabled: !!submitted,
  });

  function run() {
    const v = target.trim().toLowerCase();
    if (!v || !isValidDomain(v)) return;
    setSubmitted(v);
  }

  return (
    <ModuleShell
      title="WHOIS / RDAP"
      description="Registration data via RDAP (IETF standard)."
      icon={<FileBadge className="h-5 w-5" />}
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
        {isFetching ? "Querying…" : "Lookup"}
      </Button>}
      loading={isLoading} error={error}
    >
      {data && (
        <Card>
          <CardHeader><CardTitle>Registration</CardTitle></CardHeader>
          <CardContent>
            <KeyValue columns={2} items={[
              { label: "Registrar", value: data.registrar || "—" },
              { label: "Created", value: fmtDate(data.created_at) },
              { label: "Expires", value: fmtDate(data.expires_at) },
              { label: "Updated", value: fmtDate(data.updated_at) },
              { label: "Nameservers", value: (data.nameservers || []).join(", ") || "—", mono: true },
              { label: "Statuses", value: (data.statuses || []).join(", ") || "—", mono: true },
              { label: "Source", value: data.source },
            ]} />
          </CardContent>
        </Card>
      )}
    </ModuleShell>
  );
}
