"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, X, Activity } from "lucide-react";
import { NAV, GROUP_LABELS, type NavItem } from "./nav";
import { cn } from "@/lib/utils";

export function Sidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const pathname = usePathname();
  const groups: { key: NonNullable<NavItem["group"]>; items: NavItem[] }[] = [
    { key: "core", items: NAV.filter((n) => n.group === "core") },
    { key: "modules", items: NAV.filter((n) => n.group === "modules") },
    { key: "data", items: NAV.filter((n) => n.group === "data") },
  ];

  return (
    <>
      {/* Mobile overlay */}
      <AnimatePresence>
        {open && (
          <motion.div
            className="fixed inset-0 z-40 bg-black/70 md:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
        )}
      </AnimatePresence>

      <aside
        className={cn(
          "fixed md:sticky top-0 left-0 z-50 md:z-30 h-screen w-72 shrink-0",
          "md:translate-x-0 transition-transform duration-200",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-full flex-col bg-[#111111] border-r border-[#262626]">
          <div className="flex items-center justify-between px-5 h-16 border-b border-[#262626]">
            <Link href="/dashboard" className="flex items-center gap-2 group" onClick={onClose}>
              <div className="grid h-9 w-9 place-items-center rounded-md bg-white text-black">
                <Shield className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold leading-none">Hello You</p>
                <p className="text-[10px] text-[#71717a] tracking-widest mt-0.5">INTEL · v1.0</p>
              </div>
            </Link>
            <button
              onClick={onClose}
              className="md:hidden p-1.5 rounded-md hover:bg-white/5 text-[#a1a1aa]"
              aria-label="Close sidebar"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
            {groups.map((g) => (
              <div key={g.key}>
                <p className="px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-[#71717a]">
                  {GROUP_LABELS[g.key]}
                </p>
                <ul className="space-y-0.5">
                  {g.items.map((item) => {
                    const active = pathname === item.href || pathname?.startsWith(item.href + "/");
                    const Icon = item.icon;
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          onClick={onClose}
                          className={cn(
                            "group relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
                            active
                              ? "bg-[#262626] text-white"
                              : "text-[#a1a1aa] hover:text-white hover:bg-[#1a1a1a]",
                          )}
                        >
                          <Icon className="h-4 w-4 shrink-0" />
                          <span className="truncate">{item.label}</span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </nav>

          <div className="border-t border-[#262626] p-4">
            <div className="flex items-center gap-2 rounded-md bg-[#0f0f0f] border border-[#262626] px-3 py-2 text-xs">
              <Activity className="h-3.5 w-3.5 text-[#22c55e]" />
              <span className="text-[#a1a1aa]">All systems operational</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
