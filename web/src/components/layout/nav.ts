import {
  LayoutDashboard, User, Mail, Phone, Globe, Server, Network, ShieldCheck, FileBadge,
  Binary, ScanSearch, Cpu, Share2, FileText, Bookmark, Settings as Cog, Shield,
  KeyRound,
} from "lucide-react";

export type NavItem = {
  label: string;
  href: string;
  icon: any;
  group?: "core" | "modules" | "data";
};

export const NAV: NavItem[] = [
  { label: "Dashboard",          href: "/dashboard",          icon: LayoutDashboard, group: "core" },
  { label: "Username Search",    href: "/username",           icon: User,            group: "modules" },
  { label: "Email Search",       href: "/email",              icon: Mail,            group: "modules" },
  { label: "Phone Lookup",       href: "/phone",              icon: Phone,           group: "modules" },
  { label: "Domain Investigation", href: "/domain",           icon: Globe,           group: "modules" },
  { label: "IP Investigation",   href: "/ip",                 icon: Server,          group: "modules" },
  { label: "DNS Lookup",         href: "/dns",                icon: Network,         group: "modules" },
  { label: "WHOIS",              href: "/whois",              icon: FileBadge,       group: "modules" },
  { label: "SSL",                href: "/ssl",                icon: ShieldCheck,     group: "modules" },
  { label: "Cert. Transparency", href: "/ct",                 icon: Binary,          group: "modules" },
  { label: "Subdomain Discovery", href: "/subdomains",        icon: ScanSearch,      group: "modules" },
  { label: "Technology Detection", href: "/tech",             icon: Cpu,             group: "modules" },
  { label: "Relationship Graph", href: "/graph",              icon: Share2,          group: "modules" },
  { label: "AI Report",          href: "/report",             icon: FileText,        group: "data" },
  { label: "Saved Investigations", href: "/investigations",   icon: Bookmark,        group: "data" },
  { label: "API Audit",          href: "/config-audit",       icon: KeyRound,        group: "data" },
  { label: "Settings",           href: "/settings",           icon: Cog,             group: "data" },
];

export const GROUP_LABELS: Record<NonNullable<NavItem["group"]>, string> = {
  core: "Overview",
  modules: "OSINT Modules",
  data: "Workspace",
};

export const MODULE_ICONS: Record<string, any> = {
  username: User, email: Mail, phone: Phone, domain: Globe, ip: Server,
  dns: Network, whois: FileBadge, ssl: ShieldCheck, ct: Binary,
  subdomain: ScanSearch, tech: Cpu,
};

export const KIND_LABEL: Record<string, string> = {
  username: "Username", email: "Email", phone: "Phone", domain: "Domain",
  ip: "IP Address", dns: "DNS", whois: "WHOIS", ssl: "SSL",
  ct: "Cert. Transparency", subdomain: "Subdomain Discovery", tech: "Technology Detection",
};
