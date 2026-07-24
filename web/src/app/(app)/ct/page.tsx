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
import { Binary, Search } from "lucide-react";
import { CodeBlock } from "@/components/modules/KeyValueGrid";
import { fmtDate, isValidDomain } from "@/lib/utils";

export default function CtPage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["ct", submitted],
    queryFn: () => Osint.ct(submitted!, 50),
    enabled: !!submitted,
  });

  function run() {
    const v = target.trim().toLowerCase();
    if (!v || !isValidDomain(v)) return;
    setSubmitted(v);
  }

  return (
    <ModuleShell
      title="Certificate Transparency"
      description="Search crt.sh for certificates logged for this domain."
      icon={<Binary className="h-5 w-5" />}
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
        {isFetching ? "Searching…" : "Search"}
      </Button>}
      loading={isLoading} error={error}
    >
      {data && (
        <Card>
          <CardHeader>
            <CardTitle>Certificates ({data.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {data.length === 0 ? (
              <p className="text-sm text-muted-foreground">No certificates found.</p>
            ) : (
              <ul className="divide-y divide-white/5 -mt-5">
                {data.map((c: any) => (
                  <li key={c.id} className="py-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-mono text-xs truncate">{c.name_value}</p>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">{fmtDate(c.not_after, false)}</span>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">Issuer: {c.issuer_name}</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </ModuleShell>
  );
}
