"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { useTargetParam } from "@/hooks/useDebouncedValue";
import { Osint } from "@/lib/api";
import { ModuleShell } from "@/components/modules/ModuleShell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger, DialogFooter, DialogClose } from "@/components/ui/dialog";
import { Server, Search, ShieldAlert, Building2, Globe } from "lucide-react";
import { ThreatChip } from "@/components/common/ThreatChip";
import { KeyValue, CodeBlock } from "@/components/modules/KeyValueGrid";
import { RiskGauge } from "@/components/charts/RiskGauge";
import { isValidIp } from "@/lib/utils";

const IpMap = dynamic(() => import("@/components/modules/IpMap").then((m) => m.IpMap), { ssr: false });

export default function IpPage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["ip", submitted],
    queryFn: () => Osint.ip(submitted!),
    enabled: !!submitted,
  });

  const [scanOpen, setScanOpen] = useState(false);
  const [scanResult, setScanResult] = useState<any>(null);
  const [scanLoading, setScanLoading] = useState(false);

  function run() {
    const v = target.trim();
    if (!isValidIp(v)) return;
    setSubmitted(v);
  }

  async function runScan() {
    if (!submitted) return;
    setScanLoading(true);
    try {
      const r = await Osint.ipPortScan(submitted, true);
      setScanResult(r);
    } catch (e: any) {
      setScanResult({ error: e?.message || "scan failed" });
    } finally {
      setScanLoading(false);
      setScanOpen(false);
    }
  }

  const geo = data?.geo;

  return (
    <ModuleShell
      title="IP Investigation"
      description="Geolocation, ASN/ISP, reverse DNS, threat intel, and authorized port scanning."
      icon={<Server className="h-5 w-5" />}
      input={
        <div>
          <Label htmlFor="ip">IP address</Label>
          <div className="relative mt-1.5">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input id="ip" value={target} onChange={(e) => setTarget(e.target.value)}
                   onKeyDown={(e) => e.key === "Enter" && run()}
                   placeholder="8.8.8.8" className="pl-9" autoFocus />
          </div>
        </div>
      }
      run={
        <div className="flex gap-2">
          <Button onClick={run} disabled={!isValidIp(target) || isFetching}>
            {isFetching ? "Looking up…" : "Lookup"}
          </Button>
          <Dialog open={scanOpen} onOpenChange={setScanOpen}>
            <DialogTrigger asChild>
              <Button variant="ghost" disabled={!submitted || scanLoading}>
                {scanLoading ? "Scanning…" : "Authorized port scan"}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Confirm port scan authorization</DialogTitle>
                <DialogDescription>
                  Port scanning will send TCP connections to <b>{submitted}</b> on a small set of common ports.
                  Only proceed if you own this system or have written permission to test it.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <DialogClose asChild><Button variant="ghost">Cancel</Button></DialogClose>
                <Button onClick={runScan} disabled={scanLoading}>
                  I confirm · Scan now
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      }
      loading={isLoading} error={error}
      summary={data && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Risk</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center">
              <RiskGauge value={data.risk_score || 0} />
              <ThreatChip level={data.threat_level} score={data.risk_score} />
            </CardContent>
          </Card>
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Network</CardTitle>
            </CardHeader>
            <CardContent>
              <KeyValue
                columns={2}
                items={[
                  { label: "IP", value: data.ip, mono: true },
                  { label: "Reverse DNS", value: data.reverse_dns || "—", mono: true },
                  { label: "ISP", value: data.isp || "—", mono: !!data.isp },
                  { label: "ASN", value: data.asn || "—", mono: !!data.asn },
                  { label: "Country", value: geo?.country || "—", mono: !!geo?.country_code },
                  { label: "City", value: geo?.city || "—", mono: true },
                ]}
              />
            </CardContent>
          </Card>
        </div>
      )}
    >
      {data && geo?.latitude && geo?.longitude && (
        <Card>
          <CardHeader>
            <CardTitle>Approximate geolocation</CardTitle>
            <CardDescription>{geo.city || "—"}, {geo.country} · {geo.latitude.toFixed(2)}, {geo.longitude.toFixed(2)}</CardDescription>
          </CardHeader>
          <CardContent className="p-0 overflow-hidden rounded-b-xl">
            <div className="h-[280px]">
              <IpMap lat={geo.latitude} lng={geo.longitude} label={`${data.ip}${data.reverse_dns ? " · " + data.reverse_dns : ""}`} />
            </div>
          </CardContent>
        </Card>
      )}

      {data?.open_ports && data.open_ports.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Open ports (authorized scan)</CardTitle>
            <CardDescription>Common ports only.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {data.open_ports.map((p: number) => (
              <span key={p} className="chip chip-low">{p}</span>
            ))}
          </CardContent>
        </Card>
      )}

      {scanResult && (
        <Card>
          <CardHeader>
            <CardTitle>Scan result</CardTitle>
          </CardHeader>
          <CardContent>
            <CodeBlock value={scanResult} />
          </CardContent>
        </Card>
      )}
    </ModuleShell>
  );
}
