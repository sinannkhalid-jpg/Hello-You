"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Search, Activity, ShieldAlert, AlertTriangle, Bookmark, Globe, Network, FileBadge,
  ScanSearch, Cpu, Server, Mail, Phone, Binary, ShieldCheck, User, ArrowUpRight,
} from "lucide-react";
import { Dashboard } from "@/lib/api";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { ThreatTrendChart } from "@/components/charts/ThreatTrendChart";
import { RiskDonut } from "@/components/charts/RiskDonut";
import { CountryBar } from "@/components/charts/CountryBar";
import { KindBar } from "@/components/charts/KindBar";
import { SkeletonList } from "@/components/common/SkeletonList";
import { ThreatChip } from "@/components/common/ThreatChip";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fmtRelative } from "@/lib/utils";
import { NetworkScan } from "@/components/effects/NetworkScan";
import { RiskGauge } from "@/components/charts/RiskGauge";
import { LiveInvestigation } from "@/components/modules/LiveInvestigation";

const KIND_ICON: Record<string, any> = {
  username: User, email: Mail, phone: Phone, domain: Globe, ip: Server,
  dns: Network, whois: FileBadge, ssl: ShieldCheck, ct: Binary,
  subdomain: ScanSearch, tech: Cpu,
};

export default function DashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: Dashboard.get });

  const stats = data?.stats ?? { total: 0, favorites: 0, by_kind: {}, by_threat: {} };
  const recent = data?.recent_investigations ?? [];
  const timeline = data?.timeline ?? [];
  const riskDist = data?.risk_distribution ?? { low: 0, medium: 0, high: 0, critical: 0 };
  const countryDist = data?.country_distribution ?? {};
  const byKind = data?.stats?.by_kind ?? {};
  const avgRisk = recent.length
    ? Math.round(recent.reduce((s: number, r: any) => s + (r.risk_score || 0), 0) / recent.length)
    : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Threat intelligence overview and recent activity."
        icon={<Activity className="h-5 w-5" />}
      />

      {/* Stats row */}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Investigations" value={stats.total} icon={Search} accent="cyan" />
        <StatCard title="Favorites" value={stats.favorites} icon={Bookmark} accent="violet" />
        <StatCard title="Avg. Risk (last 10)" value={avgRisk} icon={ShieldAlert} accent={avgRisk >= 50 ? "red" : avgRisk >= 25 ? "amber" : "green"} />
        <StatCard title="Critical Findings" value={stats.by_threat?.critical ?? 0} icon={AlertTriangle} accent="red" />
      </div>

      {/* Hero with risk gauge + scan */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Overall risk posture</CardTitle>
            <CardDescription>Aggregated risk score across recent investigations.</CardDescription>
          </CardHeader>
          <CardContent>
            <RiskGauge value={avgRisk} label="Average risk" />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Investigation timeline</CardTitle>
            <CardDescription>Last 14 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <ThreatTrendChart data={timeline} />
          </CardContent>
        </Card>
      </div>

      {/* Charts row */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Risk distribution</CardTitle>
            <CardDescription>By threat level.</CardDescription>
          </CardHeader>
          <CardContent><RiskDonut data={riskDist} /></CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Investigations by module</CardTitle>
            <CardDescription>Most-used OSINT tools.</CardDescription>
          </CardHeader>
          <CardContent><KindBar data={byKind} /></CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Geo distribution</CardTitle>
            <CardDescription>IP / email origin signals.</CardDescription>
          </CardHeader>
          <CardContent><CountryBar data={countryDist} /></CardContent>
        </Card>
      </div>

      {/* Recent + activity */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent investigations</CardTitle>
              <CardDescription>Click to inspect a past result.</CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm">
              <Link href="/investigations">View all <ArrowUpRight className="h-3.5 w-3.5" /></Link>
            </Button>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <SkeletonList rows={5} />
            ) : recent.length === 0 ? (
              <div className="text-sm text-muted-foreground py-8 text-center">
                No investigations yet. Use the sidebar to start one.
              </div>
            ) : (
              <ul className="divide-y divide-white/5">
                {recent.map((r: any) => {
                  const Icon = KIND_ICON[r.kind] || Search;
                  return (
                    <li key={r.id}>
                      <Link
                        href={`/investigations/${r.id}`}
                        className="flex items-center gap-3 py-3 hover:bg-white/5 rounded-md px-2 -mx-2 transition-colors"
                      >
                        <div className="grid h-9 w-9 place-items-center rounded-md bg-white/5 border border-white/10 text-cyan-200">
                          <Icon className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate">{r.title || r.target}</p>
                          <p className="text-xs text-muted-foreground truncate">
                            {r.kind.toUpperCase()} · {fmtRelative(r.created_at)}
                          </p>
                        </div>
                        <ThreatChip level={r.threat_level} score={r.risk_score} />
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Live scan feed</CardTitle>
            <CardDescription>Sample network telemetry.</CardDescription>
          </CardHeader>
          <CardContent><NetworkScan /></CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <LiveInvestigation initialKind="domain" initialTarget="example.com" />
        <LiveInvestigation initialKind="ip" initialTarget="8.8.8.8" />
      </div>

      <motion.p
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
        className="text-xs text-muted-foreground text-center pt-6"
      >
        All lookups use only publicly available, free OSINT sources. Educational use only.
      </motion.p>
    </div>
  );
}
