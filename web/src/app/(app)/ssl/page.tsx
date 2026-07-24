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
import { ShieldCheck, Search } from "lucide-react";
import { KeyValue } from "@/components/modules/KeyValueGrid";
import { fmtDate, isValidDomain } from "@/lib/utils";

export default function SslPage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["ssl", submitted],
    queryFn: () => Osint.ssl(submitted!),
    enabled: !!submitted,
  });

  function run() {
    const v = target.trim().toLowerCase();
    if (!v || !isValidDomain(v)) return;
    setSubmitted(v);
  }

  return (
    <ModuleShell
      title="SSL Certificate"
      description="Inspect the live TLS certificate served on port 443."
      icon={<ShieldCheck className="h-5 w-5" />}
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
        {isFetching ? "Inspecting…" : "Inspect"}
      </Button>}
      loading={isLoading} error={error}
    >
      {data && (
        <Card>
          <CardHeader><CardTitle>Certificate</CardTitle></CardHeader>
          <CardContent>
            <KeyValue columns={2} items={[
              { label: "Issuer", value: data.issuer, mono: true },
              { label: "Subject", value: data.subject, mono: true },
              { label: "Valid from", value: fmtDate(data.valid_from) },
              { label: "Valid to", value: fmtDate(data.valid_to) },
              { label: "Days remaining", value: data.days_remaining ?? "—" },
              { label: "Signature", value: data.signature_algorithm, mono: true },
              { label: "Public key", value: data.public_key_algorithm, mono: true },
              { label: "SHA-256", value: data.fingerprint_sha256, mono: true },
              { label: "SANs", value: (data.san || []).join(", "), mono: true },
            ]} />
          </CardContent>
        </Card>
      )}
    </ModuleShell>
  );
}
