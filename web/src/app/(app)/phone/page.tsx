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
import { Phone, Search, MapPin, Building2, Clock } from "lucide-react";
import { KeyValue } from "@/components/modules/KeyValueGrid";

export default function PhonePage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["phone", submitted],
    queryFn: () => Osint.phone(submitted!),
    enabled: !!submitted,
  });

  function run() {
    const v = target.trim();
    if (!v) return;
    setSubmitted(v);
  }

  return (
    <ModuleShell
      title="Phone Lookup"
      description="Public metadata only — country, region, timezone, type. No PII."
      icon={<Phone className="h-5 w-5" />}
      input={
        <div>
          <Label htmlFor="p">Phone number</Label>
          <div className="relative mt-1.5">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input id="p" value={target} onChange={(e) => setTarget(e.target.value)}
                   onKeyDown={(e) => e.key === "Enter" && run()}
                   placeholder="+1 415 555 2671" className="pl-9" autoFocus />
          </div>
        </div>
      }
      run={<Button onClick={run} disabled={!target.trim() || isFetching}>
        {isFetching ? "Looking up…" : "Lookup"}
      </Button>}
      loading={isLoading} error={error}
      summary={data && data.country && (
        <Card>
          <CardContent className="p-5 flex items-center gap-4">
            <div className="text-5xl">{data.flag_emoji}</div>
            <div>
              <p className="text-2xl font-semibold">{data.country}</p>
              <p className="text-sm text-muted-foreground">{data.region || "—"}</p>
            </div>
          </CardContent>
        </Card>
      )}
    >
      {data && (
        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent>
            <KeyValue
              columns={3}
              items={[
                { label: "E.164", value: data.e164, mono: true },
                { label: "Country code", value: data.country_code, mono: true },
                { label: "Number type", value: data.number_type },
                { label: "Carrier", value: data.carrier || <span className="text-muted-foreground">unknown</span>, mono: !!data.carrier },
                { label: "Timezone", value: <span className="inline-flex items-center gap-1"><Clock className="h-3 w-3" /> {data.timezone || "—"}</span> },
                { label: "Region", value: <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" /> {data.region || "—"}</span> },
              ]}
            />
          </CardContent>
        </Card>
      )}
    </ModuleShell>
  );
}
