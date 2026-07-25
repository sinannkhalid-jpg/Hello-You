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
import {
  Mail, Search, ShieldCheck, ShieldAlert, Server, Lock, KeyRound,
  AlertTriangle, Building, FileBadge, Github, Globe, Hash, Eye, ExternalLink,
  CheckCircle2, XCircle, AlertOctagon,
} from "lucide-react";
import { ThreatChip } from "@/components/common/ThreatChip";
import { KeyValue } from "@/components/modules/KeyValueGrid";
import { RiskGauge } from "@/components/charts/RiskGauge";
import { fmtDate, isValidEmail, cn } from "@/lib/utils";
import { motion } from "framer-motion";

/* ------------------------------------------------------------------ */
/* Provider status chip                                               */
/* ------------------------------------------------------------------ */
function ProviderStatusChip({ name, status }: { name: string; status: any }) {
  if (!status) return null;
  const s = status.status || "unknown";
  let color = "border-[#262626] bg-[#0f0f0f]";
  let icon = <AlertOctagon className="h-3.5 w-3.5 text-[#a1a1aa]" />;
  let label = s;
  if (s === "ok" || s === "enabled" || s === "registered" || s === "configured" || s === "no_breaches_found") {
    color = "border-[#22c55e]/30 bg-[#22c55e]/5";
    icon = <CheckCircle2 className="h-3.5 w-3.5 text-[#22c55e]" />;
    label = "Success";
  } else if (s === "no_record" || s === "no_breaches" || s === "no_commits" || s === "no_data") {
    color = "border-[#262626] bg-[#0f0f0f]";
    icon = <CheckCircle2 className="h-3.5 w-3.5 text-white" />;
    label = s === "no_data" ? "No data" : s === "no_commits" ? "No commits" : s === "no_record" ? "No record" : "No breaches";
  } else if (s === "no_api_key" || s === "missing_key") {
    color = "border-[#f59e0b]/30 bg-[#f59e0b]/5";
    icon = <KeyRound className="h-3.5 w-3.5 text-[#f59e0b]" />;
    label = "Missing key";
  } else if (s === "not_configured" || s === "disabled" || s === "lookup_failed") {
    color = "border-[#262626] bg-[#0f0f0f]";
    icon = <XCircle className="h-3.5 w-3.5 text-[#a1a1aa]" />;
    label = s === "not_configured" ? "Not configured" : s === "lookup_failed" ? "Lookup failed" : "Disabled";
  } else if (s === "blocked" || s === "rate_limited") {
    color = "border-[#ef4444]/30 bg-[#ef4444]/5";
    icon = <AlertTriangle className="h-3.5 w-3.5 text-[#ef4444]" />;
    label = s === "rate_limited" ? "Rate-limited" : "Blocked";
  } else if (s === "not_supported") {
    color = "border-[#f59e0b]/30 bg-[#f59e0b]/5";
    icon = <XCircle className="h-3.5 w-3.5 text-[#f59e0b]" />;
    label = "No TLS";
  } else if (s === "not_registered") {
    color = "border-[#262626] bg-[#0f0f0f]";
    icon = <AlertOctagon className="h-3.5 w-3.5 text-[#a1a1aa]" />;
    label = "Not registered";
  }
  return (
    <div className={cn("rounded-md border p-2.5 text-xs flex items-center gap-2", color)}>
      {icon}
      <span className="font-medium flex-1 text-white">{name}</span>
      <span className="text-[10px] text-[#a1a1aa]">{label}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main page                                                          */
/* ------------------------------------------------------------------ */
export default function EmailPage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["email", submitted],
    queryFn: () => Osint.email(submitted!),
    enabled: !!submitted,
  });

  function run() {
    const v = target.trim();
    if (!v || !isValidEmail(v)) return;
    setSubmitted(v);
  }

  const mx = data?.mx_records ?? [];
  const providers = data?.providers || {};
  const dkim = data?.dkim;
  const tls = data?.tls;
  const rep = data?.reputation;
  const breach = data?.breach_exposure;
  const gitLeaks = data?.git_leaks;
  const gravatarProfile = data?.gravatar_profile;
  const domainAge = data?.domain_age;

  return (
    <ModuleShell
      title="Email Investigation"
      description="DNS, SPF, DKIM, DMARC, MTA-STS, TLS, BIMI, DNSSEC, RDAP, breach exposure, Gravatar, git leaks, reputation."
      icon={<Mail className="h-5 w-5" />}
      input={
        <div>
          <Label htmlFor="e">Email</Label>
          <div className="relative mt-1.5">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input id="e" type="email" value={target} onChange={(e) => setTarget(e.target.value)}
                   onKeyDown={(e) => e.key === "Enter" && run()}
                   placeholder="name@example.com" className="pl-9" autoFocus />
          </div>
        </div>
      }
      run={<Button onClick={run} disabled={!isValidEmail(target) || isFetching}>
        {isFetching ? "Investigating…" : "Investigate"}
      </Button>}
      loading={isLoading} error={error}
      summary={data && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Reputation</CardTitle>
              <CardDescription>0-100, higher = safer.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center">
              <RiskGauge value={rep?.score || 0} label="Reputation" />
              <div className="mt-2"><ThreatChip level={rep?.threat_level || "low"} score={rep?.score} /></div>
              {rep?.findings && rep.findings.length > 0 && (
                <ul className="mt-3 w-full space-y-1 text-[11px] text-[#a1a1aa]">
                  {rep.findings.slice(0, 4).map((f: string, i: number) => (
                    <li key={i} className="flex items-start gap-1">
                      <span className="text-[#f59e0b]">•</span> {f}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <KeyValue
                columns={2}
                items={[
                  { label: "Email", value: data.email, mono: true },
                  { label: "Domain", value: data.domain, mono: true },
                  { label: "Provider", value: (
                    <span className="inline-flex items-center gap-1.5">
                      <Building className="h-3 w-3 text-white" />
                      {data.provider || "—"}
                    </span>
                  ) },
                  { label: "Free mail", value: data.is_free_mail ? "yes" : "no" },
                  { label: "Disposable", value: data.is_disposable ? "yes" : "no" },
                  { label: "Domain age", value: domainAge?.age_days != null ? `${domainAge.age_days} days` : "— not available —" },
                  { label: "Registrar", value: domainAge?.registrar || "— not available —" },
                  { label: "Breach exposure", value: breach?.found ? `${breach.count} breach(es)` : breach?.configured === false ? "HIBP not configured" : "no data" },
                ]}
              />
              <div className="mt-4 grid grid-cols-3 sm:grid-cols-6 gap-2">
                <AuthChip label="SPF" ok={!!data?.spf} />
                <AuthChip label="DKIM" ok={!!dkim?.found} />
                <AuthChip label="DMARC" ok={!!data?.dmarc} />
                <AuthChip label="MTA-STS" ok={!!data?.mta_sts?.enabled} />
                <AuthChip label="TLS" ok={tls?.supports_tls > 0} />
                <AuthChip label="DNSSEC" ok={!!data?.dnssec?.enabled} />
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    >
      {data && (
        <div className="space-y-4">
          {/* Provider diagnostics */}
          <Card>
            <CardHeader>
              <CardTitle>Provider diagnostics</CardTitle>
              <CardDescription>Why information may be missing.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                {Object.entries(providers).map(([k, v]) => (
                  <ProviderStatusChip key={k} name={k} status={v} />
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Authentication details */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Email authentication</CardTitle>
                <CardDescription>SPF / DKIM / DMARC / MTA-STS / BIMI presence.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <AuthRow label="SPF" record={data.spf} />
                <AuthRowDKIM dkim={dkim} />
                <AuthRow label="DMARC" record={data.dmarc} />
                <AuthRowMTASTS mtaSts={data.mta_sts} />
                <AuthRow label="BIMI" record={data.bimi} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>MX records & TLS</CardTitle>
                <CardDescription>{mx.length} record(s), STARTTLS support.</CardDescription>
              </CardHeader>
              <CardContent>
                {mx.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No MX records found.</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {mx.map((m: any, i: number) => {
                      const t = tls?.details?.find((d: any) => d.host === m.host);
                      return (
                        <li key={i} className="flex items-center gap-2">
                          <Server className="h-3.5 w-3.5 text-white" />
                          <span className="font-mono text-xs text-[#a1a1aa]">priority {m.priority}</span>
                          <span className="font-mono">{m.host}</span>
                          {t && (
                            <span className={cn(
                              "ml-auto inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded",
                              t.tls ? "bg-[#22c55e]/10 text-[#22c55e] border border-[#22c55e]/30" : "bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/30",
                            )}>
                              <Lock className="h-3 w-3" />
                              {t.tls ? "STARTTLS" : "no TLS"}
                            </span>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
                {tls && (
                  <p className="mt-3 text-xs text-muted-foreground">
                    {tls.supports_tls}/{tls.checked} hosts support STARTTLS
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Public profile (Gravatar) */}
          {data.gravatar_url && (
            <Card>
              <CardHeader>
                <CardTitle>Gravatar / public avatar</CardTitle>
                <CardDescription>Public profile linked to this email.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-start gap-3">
                  <img src={data.gravatar_url.replace('?d=404', '?s=80&d=identicon')}
                       alt="avatar" className="h-16 w-16 rounded-md" />
                  <div className="flex-1 min-w-0">
                    {gravatarProfile ? (
                      <>
                        <p className="text-sm font-medium">{gravatarProfile.display_name || "—"}</p>
                        {gravatarProfile.bio && (
                          <p className="text-xs text-muted-foreground mt-1">{gravatarProfile.bio}</p>
                        )}
                        {gravatarProfile.location && (
                          <p className="text-[11px] text-muted-foreground mt-0.5">📍 {gravatarProfile.location}</p>
                        )}
                        {gravatarProfile.links && gravatarProfile.links.length > 0 && (
                          <ul className="mt-2 space-y-0.5">
                            {gravatarProfile.links.slice(0, 5).map((l: any, i: number) => (
                              l.url ? <li key={i} className="text-[11px]">
                                <a href={l.url} target="_blank" rel="noreferrer noopener"
                                   className="text-white hover:text-white/80 inline-flex items-center gap-1 underline underline-offset-2 decoration-[#404040]">
                                  <Globe className="h-3 w-3" /> {l.label || l.url}
                                  <ExternalLink className="h-2.5 w-2.5" />
                                </a>
                              </li> : null
                            ))}
                          </ul>
                        )}
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">Avatar exists, no public profile.</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Public git leaks */}
          {gitLeaks && (
            <Card>
              <CardHeader>
                <CardTitle>
                  <span className="inline-flex items-center gap-2">
                    <Github className="h-4 w-4" /> Public Git commits
                  </span>
                </CardTitle>
                <CardDescription>GitHub commits authored with this email.</CardDescription>
              </CardHeader>
              <CardContent>
                {gitLeaks.found && gitLeaks.commits.length > 0 ? (
                  <ul className="space-y-2 text-xs">
                  {gitLeaks.commits.map((c: any, i: number) => (
                    <li key={i} className="rounded border border-[#262626] p-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-white">{c.repo}</span>
                        <span className="text-[#a1a1aa]">·</span>
                        <span className="text-[#a1a1aa]">{c.date?.slice(0, 10)}</span>
                      </div>
                      <p className="text-[#a1a1aa] mt-0.5 break-all">{c.message}</p>
                      {c.url && (
                        <a href={c.url} target="_blank" rel="noreferrer noopener"
                           className="text-[10px] text-white hover:text-white/80 inline-flex items-center gap-1 mt-1 underline underline-offset-2 decoration-[#404040]">
                          <ExternalLink className="h-2.5 w-2.5" /> {c.url.slice(0, 60)}...
                        </a>
                      )}
                    </li>
                  ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No public commits found for this email.</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Breach exposure */}
          {breach && breach.configured && breach.found && breach.samples && breach.samples.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>
                  <span className="inline-flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-[#ef4444]" />
                    Breach exposure ({breach.count})
                  </span>
                </CardTitle>
                <CardDescription>Known data breaches this email appears in.</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-xs">
                  {breach.samples.map((b: any, i: number) => (
                    <li key={i} className="rounded border border-[#262626] p-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{b.name}</span>
                        {b.is_verified && <span className="text-[#22c55e] text-[10px]">✓ verified</span>}
                        {b.is_sensitive && <span className="text-[#ef4444] text-[10px]">⚠ sensitive</span>}
                        <span className="ml-auto text-[#a1a1aa]">{b.breach_date}</span>
                      </div>
                      {b.data_classes && b.data_classes.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {b.data_classes.map((c: string, j: number) => (
                            <span key={j} className="rounded bg-[#1a1a1a] text-[#a1a1aa] border border-[#262626] px-1.5 py-0.5 text-[10px]">
                              {c}
                            </span>
                          ))}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </ModuleShell>
  );
}

function AuthChip({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className={`rounded-md border p-2.5 text-center ${ok ? "border-[#22c55e]/30 bg-[#22c55e]/5" : "border-[#ef4444]/30 bg-[#ef4444]/5"}`}>
      <div className="flex items-center justify-center gap-1.5 text-xs font-medium">
        {ok ? <ShieldCheck className="h-3.5 w-3.5 text-[#22c55e]" /> : <ShieldAlert className="h-3.5 w-3.5 text-[#ef4444]" />}
        <span className={ok ? "text-[#22c55e]" : "text-[#ef4444]"}>{label}</span>
      </div>
      <p className="text-[10px] text-[#a1a1aa] mt-1">{ok ? "configured" : "missing"}</p>
    </div>
  );
}

function AuthRow({ label, record }: { label: string; record?: string | null }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="font-mono text-xs mt-0.5 break-all">{record || "— not published —"}</p>
    </div>
  );
}

function AuthRowDKIM({ dkim }: { dkim?: any }) {
  if (!dkim || !dkim.found) {
    return (
      <div>
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">DKIM</p>
        <p className="font-mono text-xs mt-0.5 break-all">— not published —</p>
      </div>
    );
  }
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-[#a1a1aa]">
        DKIM <span className="text-[#22c55e]">(selector: {dkim.selector})</span>
      </p>
      <p className="font-mono text-xs mt-0.5 break-all">{(dkim.value || "").slice(0, 80)}…</p>
    </div>
  );
}

function AuthRowMTASTS({ mtaSts }: { mtaSts?: any }) {
  if (!mtaSts || !mtaSts.enabled) {
    return (
      <div>
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">MTA-STS</p>
        <p className="font-mono text-xs mt-0.5">— not enabled —</p>
      </div>
    );
  }
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-[#a1a1aa]">
        MTA-STS <span className="text-[#22c55e]">({mtaSts.mode})</span>
      </p>
      <p className="font-mono text-xs mt-0.5 break-all">{(mtaSts.policy || "").slice(0, 100)}</p>
    </div>
  );
}
