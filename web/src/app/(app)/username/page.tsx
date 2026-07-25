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
  User, Search, ExternalLink, CheckCircle2, XCircle, AlertTriangle,
  ShieldOff, Globe,
} from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";
import { fmtRelative, cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

/* ------------------------------------------------------------------ */
/* Platform logo — uses the platform name as a unique short letter.   */
/* ------------------------------------------------------------------ */
const PLATFORM_LOGO: Record<string, { letter: string; gradient: string }> = {
  GitHub:     { letter: "GH", gradient: "from-slate-500 to-slate-700" },
  GitLab:     { letter: "GL", gradient: "from-orange-500 to-red-600" },
  Bitbucket:  { letter: "BB", gradient: "from-blue-500 to-cyan-600" },
  Reddit:     { letter: "R",  gradient: "from-orange-600 to-red-700" },
  Instagram:  { letter: "IG", gradient: "from-fuchsia-500 to-pink-500" },
  TikTok:     { letter: "TT", gradient: "from-cyan-400 to-fuchsia-500" },
  "Twitter/X":{ letter: "X",  gradient: "from-slate-700 to-black" },
  Threads:    { letter: "@",  gradient: "from-slate-700 to-black" },
  LinkedIn:   { letter: "in", gradient: "from-sky-600 to-blue-700" },
  Pinterest:  { letter: "P",  gradient: "from-rose-500 to-red-600" },
  YouTube:    { letter: "YT", gradient: "from-red-500 to-red-700" },
  Twitch:     { letter: "TW", gradient: "from-violet-500 to-purple-700" },
  Steam:      { letter: "ST", gradient: "from-slate-600 to-slate-800" },
  Spotify:    { letter: "SP", gradient: "from-emerald-500 to-green-700" },
  Snapchat:   { letter: "SC", gradient: "from-yellow-400 to-yellow-600" },
  Telegram:   { letter: "TG", gradient: "from-sky-400 to-blue-500" },
  Behance:    { letter: "BH", gradient: "from-blue-500 to-blue-700" },
  Dribbble:   { letter: "DR", gradient: "from-rose-400 to-pink-600" },
  Vimeo:      { letter: "V",  gradient: "from-cyan-500 to-blue-500" },
  SoundCloud: { letter: "SC", gradient: "from-orange-500 to-amber-600" },
  Gravatar:   { letter: "G",  gradient: "from-emerald-500 to-teal-700" },
  Medium:     { letter: "M",  gradient: "from-slate-600 to-slate-800" },
  "About.me": { letter: "A",  gradient: "from-violet-500 to-purple-700" },
  Mastodon:   { letter: "MA", gradient: "from-violet-500 to-indigo-700" },
  Keybase:    { letter: "KB", gradient: "from-emerald-500 to-teal-600" },
  HackerNews: { letter: "HN", gradient: "from-orange-500 to-red-600" },
  "StackOverflow": { letter: "SO", gradient: "from-orange-400 to-orange-700" },
  "Dev.to":   { letter: "D",  gradient: "from-slate-600 to-slate-800" },
  LeetCode:   { letter: "LC", gradient: "from-amber-500 to-orange-700" },
  Codeforces: { letter: "CF", gradient: "from-blue-500 to-blue-700" },
  npm:        { letter: "N",  gradient: "from-rose-500 to-red-600" },
  DockerHub:  { letter: "DH", gradient: "from-sky-500 to-blue-700" },
  PyPI:       { letter: "PY", gradient: "from-blue-500 to-cyan-600" },
  Kaggle:     { letter: "K",  gradient: "from-cyan-500 to-blue-600" },
  Discord:    { letter: "DC", gradient: "from-indigo-500 to-indigo-700" },
};

function PlatformLogo({ name }: { name: string }) {
  const logo = PLATFORM_LOGO[name] || { letter: name.slice(0, 2).toUpperCase(), gradient: "from-slate-500 to-slate-700" };
  return (
    <div className={cn(
      "grid h-10 w-10 place-items-center rounded-md text-white text-[10px] font-bold bg-gradient-to-br border border-white/10",
      logo.gradient,
    )}>
      {logo.letter}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Profile card                                                        */
/* ------------------------------------------------------------------ */
function ProfileCard({ p, username }: { p: any; username: string }) {
  return (
    <motion.li
      initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-3 p-4 hover:bg-white/5 transition-colors"
    >
      {p.avatar_url ? (
        <img src={p.avatar_url} alt={p.platform}
             className="h-10 w-10 rounded-md object-cover" />
      ) : (
        <PlatformLogo name={p.platform} />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium truncate">{p.platform}</p>
          {p.verified && (
            <span title="Verified" className="inline-flex items-center">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" />
            </span>
          )}
          <span className="ml-auto text-[10px] text-muted-foreground">
            confidence {Math.round((p.confidence || 0) * 100)}%
          </span>
        </div>
        <p className="text-xs text-muted-foreground truncate">
          {p.display_name || p.bio || p.url}
        </p>
        {p.bio && p.display_name && (
          <p className="text-[11px] text-muted-foreground/80 truncate mt-0.5">
            {p.bio}
          </p>
        )}
      </div>
      <a href={p.url} target="_blank" rel="noreferrer noopener"
         className="text-cyan-300 hover:text-cyan-200 inline-flex items-center gap-1 text-xs shrink-0">
        Open <ExternalLink className="h-3 w-3" />
      </a>
    </motion.li>
  );
}

function BlockedCard({ p }: { p: any }) {
  return (
    <li className="flex items-center gap-3 p-3 opacity-75">
      <PlatformLogo name={p.platform} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium truncate flex items-center gap-2">
          {p.platform}
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-300">
            {p.reason}
          </span>
        </p>
        <p className="text-[11px] text-muted-foreground/70 truncate">
          {p.detail || `Platform blocked (${p.reason})`}
        </p>
      </div>
    </li>
  );
}

function NotFoundCard({ p }: { p: any }) {
  return (
    <li className="flex items-center gap-3 p-2 opacity-50">
      <div className="grid h-8 w-8 place-items-center rounded-md bg-white/5">
        <XCircle className="h-4 w-4 text-muted-foreground" />
      </div>
      <p className="text-xs text-muted-foreground">{p.platform}</p>
    </li>
  );
}

/* ------------------------------------------------------------------ */
/* Main page                                                          */
/* ------------------------------------------------------------------ */
export default function UsernamePage() {
  const { target, setTarget } = useTargetParam();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const { data, isLoading, error, isFetching } = useQuery({
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
  const blocked = data?.blocked ?? [];
  const notFound = data?.not_found ?? [];
  const totalChecked = data?.total_checked ?? 0;
  const providersBlocked = data?.providers_blocked ?? 0;
  const confidence = data?.confidence ?? 0;

  return (
    <ModuleShell
      title="Username Investigation"
      description={`Check a username against ${totalChecked || 36} public profile platforms.`}
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
        <div className="grid gap-4 sm:grid-cols-4">
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Username</p>
            <p className="mt-1 font-mono">{data.username}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Found</p>
            <p className="mt-1 text-2xl font-semibold text-emerald-300">{profiles.length}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Blocked</p>
            <p className="mt-1 text-2xl font-semibold text-rose-300">{providersBlocked}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">rate-limited / cloudflare / no API</p>
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
      {!isLoading && data && profiles.length === 0 && blocked.length === 0 && (
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
            <CardDescription>Confirmed matches with public profile data.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <ul className="divide-y divide-white/5">
              <AnimatePresence>
                {profiles.map((p: any) => (
                  <ProfileCard key={p.url} p={p} username={data.username} />
                ))}
              </AnimatePresence>
            </ul>
          </CardContent>
        </Card>
      )}

      {blocked.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldOff className="h-4 w-4 text-rose-300" />
              Blocked platforms ({blocked.length})
            </CardTitle>
            <CardDescription>
              These platforms could not be queried (rate-limited, anti-bot, or no public API). We do not assume the user doesn't exist there.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <ul className="divide-y divide-white/5">
              {blocked.map((p: any) => (
                <BlockedCard key={p.platform + p.url} p={p} />
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {notFound.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <XCircle className="h-4 w-4 text-muted-foreground" />
              Not found on {notFound.length} platform{notFound.length === 1 ? "" : "s"}
            </CardTitle>
            <CardDescription>Platforms that explicitly returned "no match".</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-1">
              {notFound.map((p: any) => (
                <NotFoundCard key={p.platform} p={p} />
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </ModuleShell>
  );
}
