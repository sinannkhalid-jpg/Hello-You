"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Shield, Search, Network, FileBadge, ScanSearch, Share2, ArrowRight, CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Typewriter } from "@/components/effects/Typewriter";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Landing() {
  const { user, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && user) router.replace("/dashboard");
  }, [ready, user, router]);

  return (
    <div className="min-h-screen bg-[#090909]">
      <header className="px-4 sm:px-6 h-16 flex items-center justify-between max-w-7xl mx-auto border-b border-[#262626]">
        <Link href="/" className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-md bg-white text-black">
            <Shield className="h-4 w-4" />
          </div>
          <span className="font-semibold">Hello You</span>
        </Link>
        <nav className="flex items-center gap-2">
          <Link href="/login"><Button variant="ghost" size="sm">Sign in</Button></Link>
          <Link href="/register"><Button size="sm">Get started</Button></Link>
        </nav>
      </header>

      <section className="px-4 sm:px-6 max-w-7xl mx-auto pt-10 sm:pt-20 pb-20 text-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
          className="inline-flex items-center gap-2 rounded-full border border-[#262626] bg-[#151515] px-3 py-1 text-xs text-[#a1a1aa]"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-[#22c55e]" />
          Educational platform · Public data only
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.05 }}
          className="mt-6 text-4xl sm:text-6xl font-semibold tracking-tight text-balance"
        >
          Cyber intelligence, <br className="hidden sm:block" />
          <span className="text-white">democratized for learning.</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }}
          className="mt-5 text-[#a1a1aa] max-w-2xl mx-auto"
        >
          Investigate usernames, emails, domains, IPs and certificates using only
          publicly available signals. Build relationship graphs, generate AI-style
          reports, and export PDF/CSV/JSON.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.18 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <Link href="/register"><Button size="lg">Create free account <ArrowRight className="h-4 w-4" /></Button></Link>
          <Link href="/login"><Button variant="secondary" size="lg">Sign in</Button></Link>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-8 font-mono text-sm text-[#a1a1aa]"
        >
          <Typewriter words={["$ init scan --target example.com", "$ resolving dns…", "$ verified tls chain", "$ found 4 subdomains", "$ risk: low"]} />
        </motion.div>
      </section>

      <section className="px-4 sm:px-6 max-w-7xl mx-auto pb-20 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.05 * i }}
          >
            <div className="rounded-xl border border-[#262626] bg-[#151515] p-5 h-full card-hover">
              <div className="grid h-10 w-10 place-items-center rounded-md bg-[#1a1a1a] border border-[#262626] text-white">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-3 font-semibold">{f.title}</h3>
              <p className="text-sm text-[#a1a1aa] mt-1">{f.desc}</p>
            </div>
          </motion.div>
        ))}
      </section>

      <section className="px-4 sm:px-6 max-w-5xl mx-auto pb-24">
        <div className="rounded-2xl border border-[#262626] bg-[#151515] p-6 sm:p-8 grid gap-6 sm:grid-cols-2 items-center">
          <div>
            <h2 className="text-2xl font-semibold">Built responsibly</h2>
            <ul className="mt-4 space-y-2 text-sm text-[#a1a1aa]">
              {[
                "Only public, free OSINT sources are used.",
                "No scraping behind logins, no credential abuse.",
                "Port scanning is gated behind explicit authorization.",
                "Every lookup is logged for transparency and audit.",
              ].map((b) => (
                <li key={b} className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 mt-0.5 text-[#22c55e]" />
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-[#262626] bg-[#0a0a0a] p-4 font-mono text-xs text-[#a1a1aa]">
            {`$ curl -X POST $API/api/v1/dns/example.com -H "Authorization: Bearer …"
{ "a": ["93.184.216.34"], "aaaa": [], "mx": [{"priority": 10, "host": "…"}], … }`}
          </div>
        </div>
      </section>

      <footer className="px-4 sm:px-6 max-w-7xl mx-auto pb-10 text-xs text-[#a1a1aa] flex flex-wrap items-center justify-between gap-2">
        <p>© {new Date().getFullYear()} Hello You · Educational use only.</p>
        <p>v1.0.0</p>
      </footer>
    </div>
  );
}

const FEATURES = [
  { title: "Username enumeration",   desc: "Check 36 public platforms instantly.", icon: Search },
  { title: "Domain & DNS intel",     desc: "A/AAAA/MX/NS/TXT/SOA/CAA, DNSSEC, subdomains via CT logs.", icon: Network },
  { title: "SSL & certificates",     desc: "Real TLS handshake, X.509 parsing, chain validation.", icon: Shield },
  { title: "WHOIS via RDAP",         desc: "IETF-standard registration data from registries.", icon: FileBadge },
  { title: "Tech fingerprinting",    desc: "Detect 30+ frameworks, servers, CDNs, analytics.", icon: ScanSearch },
  { title: "Relationship graphs",    desc: "Auto-derived entity graphs you can pan, zoom, drag.", icon: Share2 },
];
