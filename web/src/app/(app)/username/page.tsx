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
import { User, Search, ExternalLink, CheckCircle2, XCircle } from "lucide-react";
import { ThreatChip } from "@/components/common/ThreatChip";
import { EmptyState } from "@/components/common/EmptyState";
import { fmtRelative, cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

export default function UsernamePage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["username", submitted],
    queryFn: () => Osint.username(submitted!),
    enabled: !!submitted,
  });

  function run() {
    const v = target.trim();
    if (!v) return;
    setSubmitted(v);
  }

  const profiles = data?.profiles ?? [];
  const confidence = data?.confidence ?? 0;

  return (
    <ModuleShell
      title="Username Investigation"
      description="Check a username against 20+ public profile platforms."
      icon={<User className="h-5 w-5" />}
      input={
        <div>
          <Label htmlFor="u">Username</Label>
          <div className="relative mt-1.5">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input id="u" autoFocus value={target} onChange={(e) => setTarget(e.target.value)}
                   onKeyDown={(e) => e.key === "Enter" && run()}
                   placeholder="e.g. octocat" className="pl-9" />
          </div>
        </div>
      }
      run={<Button onClick={run} disabled={!target.trim() || isFetching}>
        {isFetching ? "Scanning…" : "Investigate"}
      </Button>}
      loading={isLoading}
      error={error}
      summary={data && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Username</p>
            <p className="mt-1 font-mono">{data.username}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Profiles found</p>
            <p className="mt-1 text-2xl font-semibold">{profiles.length}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Confidence</p>
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-cyan-400 to-violet-400" style={{ width: `${Math.round(confidence * 100)}%` }} />
              </div>
              <span className="text-sm">{Math.round(confidence * 100)}%</span>
            </div>
          </CardContent></Card>
        </div>
      )}
    >
      {!isLoading && data && profiles.length === 0 && (
        <EmptyState
          icon={<XCircle className="h-6 w-6" />}
          title="No profiles found"
          description="We didn't find a public profile matching this username on the platforms we check."
        />
      )}
      {profiles.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Detected profiles ({profiles.length})</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ul className="divide-y divide-white/5">
              <AnimatePresence>
                {profiles.map((p: any) => (
                  <motion.li
                    key={p.url}
                    initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-3 p-4 hover:bg-white/5 transition-colors"
                  >
                    <div className="grid h-10 w-10 place-items-center rounded-md bg-gradient-to-br from-cyan-500/20 to-violet-500/20 border border-white/10">
                      <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">{p.platform}</p>
                      <p className="text-xs text-muted-foreground truncate">{p.bio || p.url}</p>
                    </div>
                    <a href={p.url} target="_blank" rel="noreferrer noopener"
                       className="text-cyan-300 hover:text-cyan-200 inline-flex items-center gap-1 text-xs">
                      Open <ExternalLink className="h-3 w-3" />
                    </a>
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          </CardContent>
        </Card>
      )}
    </ModuleShell>
  );
}
