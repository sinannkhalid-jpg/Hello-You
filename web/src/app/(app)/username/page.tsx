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
  GitHub:     { letter: "GH", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  GitLab:     { letter: "GL", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Bitbucket:  { letter: "BB", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Reddit:     { letter: "R",  gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Instagram:  { letter: "IG", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  TikTok:     { letter: "TT", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  "Twitter/X":{ letter: "X",  gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Threads:    { letter: "@",  gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  LinkedIn:   { letter: "in", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Pinterest:  { letter: "P",  gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  YouTube:    { letter: "YT", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Twitch:     { letter: "TW", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Steam:      { letter: "ST", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Spotify:    { letter: "SP", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Snapchat:   { letter: "SC", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Telegram:   { letter: "TG", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Behance:    { letter: "BH", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Dribbble:   { letter: "DR", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Vimeo:      { letter: "V",  gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  SoundCloud: { letter: "SC", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Gravatar:   { letter: "G",  gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Medium:     { letter: "M",  gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  "About.me": { letter: "A",  gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Mastodon:   { letter: "MA", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Keybase:    { letter: "KB", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  HackerNews: { letter: "HN", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  "StackOverflow": { letter: "SO", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  "Dev.to":   { letter: "D",  gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  LeetCode:   { letter: "LC", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Codeforces: { letter: "CF", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  npm:        { letter: "N",  gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  DockerHub:  { letter: "DH", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  PyPI:       { letter: "PY", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Kaggle:     { letter: "K",  gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
  Discord:    { letter: "DC", gradient: "from-[#1a1a1a] to-[#0f0f0f]" },
};

function PlatformLogo({ name }: { name: string }) {
  const logo = PLATFORM_LOGO[name] || { letter: name.slice(0, 2).toUpperCase(), gradient: "from-[#262626] to-[#1a1a1a]" };
  return (
    <div className={cn(
      "grid h-10 w-10 place-items-center rounded-md text-white text-[10px] font-bold bg-[#1a1a1a] border border-[#262626]",
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
      className="flex items-center gap-3 p-4 hover:bg-[#1a1a1a] transition-colors"
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
              <CheckCircle2 className="h-3.5 w-3.5 text-[#22c55e]" />
            </span>
          )}
          <span className="ml-auto text-[10px] text-[#a1a1aa]">
            confidence {Math.round((p.confidence || 0) * 100)}%
          </span>
        </div>
        <p className="text-xs text-[#a1a1aa] truncate">
          {p.display_name || p.bio || p.url}
        </p>
        {p.bio && p.display_name && (
          <p className="text-[11px] text-[#71717a] truncate mt-0.5">
            {p.bio}
          </p>
        )}
      </div>
      <a href={p.url} target="_blank" rel="noreferrer noopener"
         className="text-white hover:text-white/80 inline-flex items-center gap-1 text-xs shrink-0 underline underline-offset-2 decoration-[#404040]">
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
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/30">
            {p.reason}
          </span>
        </p>
        <p className="text-[11px] text-[#71717a] truncate">
          {p.detail || `Platform blocked (${p.reason})`}
        </p>
      </div>
    </li>
  );
}

function NotFoundCard({ p }: { p: any }) {
  return (
    <li className="flex items-center gap-3 p-2 opacity-50">
      <div className="grid h-8 w-8 place-items-center rounded-md bg-[#1a1a1a] border border-[#262626]">
        <XCircle className="h-4 w-4 text-[#a1a1aa]" />
      </div>
      <p className="text-xs text-[#a1a1aa]">{p.platform}</p>
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
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#a1a1aa]" />
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
            <p className="text-xs uppercase tracking-wider text-[#a1a1aa]">Username</p>
            <p className="mt-1 font-mono">{data.username}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-[#a1a1aa]">Found</p>
            <p className="mt-1 text-2xl font-semibold text-white">{profiles.length}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-[#a1a1aa]">Blocked</p>
            <p className="mt-1 text-2xl font-semibold text-[#a1a1aa]">{providersBlocked}</p>
            <p className="text-[10px] text-[#71717a] mt-0.5">rate-limited / cloudflare / no API</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-xs uppercase tracking-wider text-[#a1a1aa]">Confidence</p>
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 h-2 rounded-full bg-[#262626] overflow-hidden">
                <div className="h-full bg-white" style={{ width: `${Math.round(confidence * 100)}%` }} />
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
            <ul className="divide-y divide-[#262626]">
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
              <ShieldOff className="h-4 w-4 text-[#a1a1aa]" />
              Blocked platforms ({blocked.length})
            </CardTitle>
            <CardDescription>
              These platforms could not be queried (rate-limited, anti-bot, or no public API). We do not assume the user doesn't exist there.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <ul className="divide-y divide-[#262626]">
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
              <XCircle className="h-4 w-4 text-[#a1a1aa]" />
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
