"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTargetParam } from "@/hooks/useDebouncedValue";
import { Osint } from "@/lib/api";
import { ModuleShell } from "@/components/modules/ModuleShell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Globe, Search, ShieldCheck, Server, Cpu, Code2, Activity, Lock, FileBadge,
} from "lucide-react";
import { ThreatChip } from "@/components/common/ThreatChip";
import { KeyValue, CodeBlock } from "@/components/modules/KeyValueGrid";
import { RiskGauge } from "@/components/charts/RiskGauge";
import { fmtDate, isValidDomain } from "@/lib/utils";

export default function DomainPage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["domain", submitted],
    queryFn: () => Osint.domain(submitted!),
    enabled: !!submitted,
  });

  function run() {
    const v = target.trim().toLowerCase();
    if (!v || !isValidDomain(v)) return;
    setSubmitted(v);
  }

  const dns = data?.dns;
  const ssl = data?.ssl;
  const whois = data?.whois;
  const techs = data?.technologies ?? [];

  return (
    <ModuleShell
      title="Domain Investigation"
      description="DNS, WHOIS, SSL, technology detection, headers — all from public signals."
      icon={<Globe className="h-5 w-5" />}
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
        {isFetching ? "Investigating…" : "Investigate"}
      </Button>}
      loading={isLoading} error={error}
      summary={data && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Risk</CardTitle>
              <CardDescription>Composite.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center">
              <RiskGauge value={data.risk_score || 0} />
              <ThreatChip level={data.threat_level} score={data.risk_score} />
            </CardContent>
          </Card>
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Infrastructure</CardTitle>
            </CardHeader>
            <CardContent>
              <KeyValue
                columns={2}
                items={[
                  { label: "CDN", value: data.cdn || "—", mono: true },
                  { label: "Server / hosting", value: data.hosting || "—", mono: true },
                  { label: "IPv4 (A)", value: (dns?.a || []).join(", ") || "—", mono: true },
                  { label: "IPv6 (AAAA)", value: (dns?.aaaa || []).join(", ") || "—", mono: true },
                  { label: "DNSSEC", value: dns?.dnssec ? "enabled" : "not enabled" },
                  { label: "Registrar", value: whois?.registrar || "—" },
                ]}
              />
            </CardContent>
          </Card>
        </div>
      )}
    >
      {data && (
        <Tabs defaultValue="dns">
          <TabsList>
            <TabsTrigger value="dns"><Activity className="h-3.5 w-3.5" /> DNS</TabsTrigger>
            <TabsTrigger value="ssl"><Lock className="h-3.5 w-3.5" /> SSL</TabsTrigger>
            <TabsTrigger value="whois"><FileBadge className="h-3.5 w-3.5" /> WHOIS</TabsTrigger>
            <TabsTrigger value="tech"><Cpu className="h-3.5 w-3.5" /> Tech ({techs.length})</TabsTrigger>
            <TabsTrigger value="headers"><Code2 className="h-3.5 w-3.5" /> Headers</TabsTrigger>
          </TabsList>

          <TabsContent value="dns">
            <Card>
              <CardContent className="p-5 space-y-5">
                <KeyValue
                  columns={2}
                  items={[
                    { label: "A", value: (dns?.a || []).join("\n") || "—", mono: true },
                    { label: "AAAA", value: (dns?.aaaa || []).join("\n") || "—", mono: true },
                    { label: "NS", value: (dns?.ns || []).join("\n") || "—", mono: true },
                    { label: "MX", value: (dns?.mx || []).map((m: any) => `${m.priority} ${m.host}`).join("\n") || "—", mono: true },
                    { label: "TXT", value: (dns?.txt || []).join("\n") || "—", mono: true },
                    { label: "CAA", value: (dns?.caa || []).map((c: any) => `${c.flag} ${c.tag} ${c.value}`).join("\n") || "—", mono: true },
                  ]}
                />
                {dns?.soa && (
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">SOA</p>
                    <CodeBlock value={dns.soa} />
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="ssl">
            <Card>
              <CardContent className="p-5">
                {ssl ? (
                  <KeyValue
                    columns={2}
                    items={[
                      { label: "Issuer", value: ssl.issuer, mono: true },
                      { label: "Subject", value: ssl.subject, mono: true },
                      { label: "Valid from", value: fmtDate(ssl.valid_from) },
                      { label: "Valid to", value: fmtDate(ssl.valid_to) },
                      { label: "Days remaining", value: ssl.days_remaining ?? "—" },
                      { label: "Signature algorithm", value: ssl.signature_algorithm, mono: true },
                      { label: "Public key", value: ssl.public_key_algorithm, mono: true },
                      { label: "SHA-256 fingerprint", value: ssl.fingerprint_sha256, mono: true },
                      { label: "SANs", value: (ssl.san || []).join(", "), mono: true },
                    ]}
                  />
                ) : <p className="text-sm text-muted-foreground">Could not retrieve a TLS certificate.</p>}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="whois">
            <Card>
              <CardContent className="p-5">
                {whois ? (
                  <KeyValue
                    columns={2}
                    items={[
                      { label: "Registrar", value: whois.registrar || "—" },
                      { label: "Created", value: fmtDate(whois.created_at) },
                      { label: "Expires", value: fmtDate(whois.expires_at) },
                      { label: "Updated", value: fmtDate(whois.updated_at) },
                      { label: "Nameservers", value: (whois.nameservers || []).join(", "), mono: true },
                      { label: "Statuses", value: (whois.statuses || []).join(", "), mono: true },
                      { label: "Source", value: whois.source },
                    ]}
                  />
                ) : <p className="text-sm text-muted-foreground">No RDAP endpoint for this TLD.</p>}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="tech">
            <Card>
              <CardContent className="p-5">
                {techs.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No technology signatures matched.</p>
                ) : (
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {techs.map((t: any) => (
                      <div key={t.name} className="rounded-md border border-white/10 bg-white/5 p-3">
                        <p className="text-sm font-medium">{t.name}</p>
                        <p className="text-xs text-muted-foreground">{t.category} · {Math.round((t.confidence || 0) * 100)}%</p>
                        {t.evidence && <p className="text-[10px] text-muted-foreground mt-1">{t.evidence}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="headers">
            <Card>
              <CardContent className="p-5">
                <CodeBlock value={data.headers || {}} />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </ModuleShell>
  );
}
