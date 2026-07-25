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
  Phone, Search, MapPin, Building2, Clock, CheckCircle2, XCircle,
  AlertOctagon, MessageCircle, ExternalLink, ShieldAlert, Smartphone,
  Lock, Briefcase, Network,
} from "lucide-react";
import { KeyValue } from "@/components/modules/KeyValueGrid";
import { cn } from "@/lib/utils";

function MessagingStatus({ name, info }: { name: string; info: any }) {
  let icon = <AlertOctagon className="h-4 w-4 text-muted-foreground" />;
  let color = "border-white/10 bg-white/5";
  let label = "Unknown";
  if (info?.available === true) {
    icon = <CheckCircle2 className="h-4 w-4 text-emerald-300" />;
    color = "border-emerald-500/30 bg-emerald-500/10";
    label = "Linked";
  } else if (info?.available === false) {
    icon = <XCircle className="h-4 w-4 text-rose-300" />;
    color = "border-rose-500/30 bg-rose-500/10";
    label = "Not linked";
  } else if (info?.reason === "no_public_api") {
    icon = <Lock className="h-4 w-4 text-amber-300" />;
    color = "border-amber-500/30 bg-amber-500/10";
    label = "Unavailable";
  } else if (info?.reason === "lookup_failed" || info?.reason === "request_failed") {
    icon = <AlertOctagon className="h-4 w-4 text-rose-300" />;
    color = "border-rose-500/30 bg-rose-500/10";
    label = "Lookup failed";
  }
  return (
    <div className={cn("rounded-md border p-3", color)}>
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm font-medium">{name}</span>
        <span className="ml-auto text-[10px] text-muted-foreground">{label}</span>
      </div>
      {info?.reason && (
        <p className="text-[11px] text-muted-foreground mt-1.5">
          <span className="text-foreground/70">Reason:</span> {info.reason}
        </p>
      )}
      {info?.detail && (
        <p className="text-[11px] text-muted-foreground/80 mt-0.5">{info.detail}</p>
      )}
      {info?.profile_url && (
        <a href={info.profile_url} target="_blank" rel="noreferrer noopener"
           className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-cyan-300 hover:text-cyan-200">
          Open <ExternalLink className="h-2.5 w-2.5" />
        </a>
      )}
      {info?.title && (
        <p className="text-[11px] text-muted-foreground mt-1">{info.title}</p>
      )}
    </div>
  );
}

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

  const messaging = data?.messaging || {};
  const reputation = data?.reputation || {};
  const portability = data?.portability || {};
  const formats = data?.formats || {};
  const timezones = data?.timezones || [];

  return (
    <ModuleShell
      title="Phone Investigation"
      description="Public metadata: country, region, timezone, type, carrier, messaging presence, portability."
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
            <div className="flex-1">
              <p className="text-2xl font-semibold">{data.country_name || data.country}</p>
              <p className="text-sm text-muted-foreground">{data.region || "—"}</p>
              {data.valid && (
                <p className="text-[11px] text-emerald-300 mt-1 inline-flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" /> valid E.164
                </p>
              )}
            </div>
            {data.confidence > 0 && (
              <div className="text-right">
                <p className="text-[10px] text-muted-foreground">Confidence</p>
                <p className="text-2xl font-semibold text-cyan-300">
                  {Math.round((data.confidence || 0) * 100)}%
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    >
      {data && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Number details</CardTitle>
            </CardHeader>
            <CardContent>
              <KeyValue
                columns={3}
                items={[
                  { label: "E.164", value: data.e164, mono: true },
                  { label: "Country code", value: data.country_code, mono: true },
                  { label: "Number type", value: data.number_type_name || data.number_type },
                  { label: "Carrier", value: data.carrier || <span className="text-muted-foreground">Unavailable</span>, mono: !!data.carrier },
                  { label: "Mobile", value: data.is_mobile ? "yes" : "no" },
                  { label: "VoIP", value: data.is_voip ? "yes" : "no" },
                  { label: "Toll-free", value: data.is_toll_free ? "yes" : "no" },
                  { label: "Premium rate", value: data.is_premium_rate ? "yes" : "no" },
                  { label: "Timezone", value: (
                    <span className="inline-flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {data.timezone || "—"}
                    </span>
                  ) },
                ]}
              />
              {Object.keys(formats).length > 0 && (
                <div className="mt-3 text-[11px] text-muted-foreground">
                  Formats: {formats.e164} · {formats.international} · {formats.national}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Messaging presence */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageCircle className="h-4 w-4" />
                Messaging presence
              </CardTitle>
              <CardDescription>Which messaging apps the number is linked to.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 sm:grid-cols-3">
                <MessagingStatus name="WhatsApp" info={messaging.whatsapp} />
                <MessagingStatus name="Telegram" info={messaging.telegram} />
                <MessagingStatus name="Signal"    info={messaging.signal} />
              </div>
            </CardContent>
          </Card>

          {/* Portability */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-4 w-4" />
                Number portability
              </CardTitle>
              <CardDescription>Original network at allocation vs current.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2 text-sm">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Original carrier</p>
                  <p className="mt-0.5 font-mono">
                    {portability.original_carrier || <span className="text-muted-foreground">Unavailable</span>}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Current carrier</p>
                  <p className="mt-0.5 font-mono">
                    {portability.current_carrier_known
                      ? <span>—</span>
                      : <span className="text-muted-foreground">Unavailable — reason: {portability.reason || "unknown"}</span>}
                  </p>
                </div>
              </div>
              {portability.reason && (
                <p className="mt-3 text-[11px] text-muted-foreground/80">
                  <span className="text-foreground/70">Reason:</span> {portability.reason}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Reputation */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4" />
                Reputation
              </CardTitle>
              <CardDescription>Spam / fraud scoring from public sources.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2 text-sm">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Spam score</p>
                  <p className="mt-0.5 font-mono">
                    {reputation.spam_score != null
                      ? reputation.spam_score
                      : <span className="text-muted-foreground">Unavailable</span>}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Fraud score</p>
                  <p className="mt-0.5 font-mono">
                    {reputation.fraud_score != null
                      ? reputation.fraud_score
                      : <span className="text-muted-foreground">Unavailable</span>}
                  </p>
                </div>
              </div>
              {reputation.reason && (
                <p className="mt-3 text-[11px] text-muted-foreground/80">
                  <span className="text-foreground/70">Reason:</span> {reputation.reason}
                  {reputation.detail && <span> — {reputation.detail}</span>}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Business association */}
          {data.business_association && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Briefcase className="h-4 w-4" /> Public business association
                </CardTitle>
              </CardHeader>
              <CardContent>
                <KeyValue items={Object.entries(data.business_association).map(([k, v]) => ({
                  label: k, value: String(v),
                }))} />
              </CardContent>
            </Card>
          )}

          {/* Data sources */}
          {data.data_sources && data.data_sources.length > 0 && (
            <div className="text-[11px] text-muted-foreground text-center">
              Sources: {data.data_sources.join(" · ")}
            </div>
          )}
        </div>
      )}
    </ModuleShell>
  );
}
