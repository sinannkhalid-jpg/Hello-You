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
import { Cpu, Search } from "lucide-react";
import { isValidDomain } from "@/lib/utils";

export default function TechPage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["tech", submitted],
    queryFn: () => Osint.tech(submitted!),
    enabled: !!submitted,
  });

  function run() {
    const v = target.trim().toLowerCase();
    if (!v || !isValidDomain(v)) return;
    setSubmitted(v);
  }

  // group by category
  const grouped: Record<string, any[]> = {};
  (data || []).forEach((t: any) => {
    grouped[t.category] = grouped[t.category] || [];
    grouped[t.category].push(t);
  });

  return (
    <ModuleShell
      title="Technology Detection"
      description="Fingerprint frameworks, servers, CDNs, and analytics from response signals."
      icon={<Cpu className="h-5 w-5" />}
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
        {isFetching ? "Detecting…" : "Detect"}
      </Button>}
      loading={isLoading} error={error}
    >
      {data && (
        <Card>
          <CardHeader><CardTitle>Detected technologies ({data.length})</CardTitle></CardHeader>
          <CardContent className="space-y-5">
            {Object.keys(grouped).length === 0 ? (
              <p className="text-sm text-muted-foreground">No technology signatures matched.</p>
            ) : Object.entries(grouped).map(([cat, items]) => (
              <div key={cat}>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">{cat}</p>
                <div className="flex flex-wrap gap-2">
                  {items.map((t: any) => (
                    <span key={t.name + cat} className="chip chip-unknown">
                      {t.name} <span className="opacity-60">· {Math.round((t.confidence || 0) * 100)}%</span>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </ModuleShell>
  );
}
