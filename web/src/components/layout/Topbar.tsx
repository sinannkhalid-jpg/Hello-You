"use client";
import { Menu, Search, LogOut, User as UserIcon, Settings as Cog, ChevronDown } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuLabel, DropdownMenuItem, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";
import Link from "next/link";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export function Topbar({ onMenu }: { onMenu: () => void }) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [q, setQ] = useState("");

  function onSearch(e: React.FormEvent) {
    e.preventDefault();
    const v = q.trim();
    if (!v) return;
    if (/^[\w.-]+@[\w.-]+\.\w+$/.test(v)) router.push(`/email?target=${encodeURIComponent(v)}`);
    else if (/^\+?\d[\d\s-]{6,}$/.test(v)) router.push(`/phone?target=${encodeURIComponent(v)}`);
    else if (/^(\d{1,3}\.){3}\d{1,3}$/.test(v)) router.push(`/ip?target=${encodeURIComponent(v)}`);
    else if (/^([a-z0-9-]+\.)+[a-z]{2,}$/i.test(v)) router.push(`/domain?target=${encodeURIComponent(v)}`);
    else router.push(`/username?target=${encodeURIComponent(v)}`);
  }

  async function onLogout() {
    try { await logout(); toast.success("Signed out"); } catch {}
    router.push("/login");
  }

  const initials = (user?.full_name || user?.email || "?")
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");

  return (
    <header className="sticky top-0 z-20 h-16 glass-strong border-b border-white/5">
      <div className="h-full px-3 sm:px-5 flex items-center gap-2 sm:gap-4">
        <Button variant="ghost" size="icon" onClick={onMenu} className="md:hidden" aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </Button>

        <form onSubmit={onSearch} className="flex-1 max-w-2xl">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Quick search — username, email, phone, domain, IP…"
              className="pl-9 h-10 bg-white/5"
              aria-label="Quick search"
            />
          </div>
        </form>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-white/5">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-gradient-to-br from-cyan-500/30 to-violet-500/30 text-foreground text-xs">
                  {initials || "?"}
                </AvatarFallback>
              </Avatar>
              <div className="hidden sm:block text-left">
                <p className="text-xs font-medium leading-none">{user?.full_name || user?.email}</p>
                <p className="text-[10px] text-muted-foreground leading-none mt-0.5">{user?.email}</p>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Signed in as</DropdownMenuLabel>
            <div className="px-2 pb-2 text-xs text-muted-foreground truncate">{user?.email}</div>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/settings"><Cog className="h-4 w-4" /> Settings</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/investigations"><UserIcon className="h-4 w-4" /> My investigations</Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onLogout} className="text-rose-300 focus:text-rose-200">
              <LogOut className="h-4 w-4" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
