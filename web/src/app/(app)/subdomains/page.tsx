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
import { ScanSearch, Search } from "lucide-react";
import { isValidDomain } from "@/lib/utils";

export default function SubdomainPage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["subs", submitted],
    queryFn: () => Osint.subdomains(submitted!),
    enabled: !!submitted,
  });

  function run() {
    const v = target.trim().toLowerCase();
    if (!v || !isValidDomain(v)) return;
    setSubmitted(v);
  }

  return (
    <ModuleShell
      title="Subdomain Discovery"
      description="Find publicly-logged subdomains via Certificate Transparency."
      icon={<ScanSearch className="h-5 w-5" />}
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
        {isFetching ? "Discovering…" : "Discover"}
      </Button>}
      loading={isLoading} error={error}
    >
      {data && (
        <Card>
          <CardHeader><CardTitle>Subdomains ({data.subdomains?.length ?? 0})</CardTitle></CardHeader>
          <CardContent>
            {(!data.subdomains || data.subdomains.length === 0) ? (
              <p className="text-sm text-muted-foreground">No subdomains found in CT logs.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {data.subdomains.map((s: string) => (
                  <span key={s} className="chip chip-unknown font-mono">{s}</span>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </ModuleShell>
  );
}
