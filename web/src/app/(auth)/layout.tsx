"use client";
import Link from "next/link";
import { Shield } from "lucide-react";
import { motion } from "framer-motion";
import { Typewriter } from "@/components/effects/Typewriter";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left: marketing panel */}
      <div className="relative hidden lg:flex flex-col p-10 overflow-hidden">
        <Link href="/" className="flex items-center gap-2 z-10">
          <div className="grid h-9 w-9 place-items-center rounded-md bg-gradient-to-br from-cyan-500 to-violet-600 shadow-[0_0_24px_rgba(0,240,255,0.4)]">
            <Shield className="h-4 w-4 text-white" />
          </div>
          <span className="font-semibold">Hello You</span>
        </Link>

        <div className="flex-1 flex flex-col justify-center z-10 max-w-md">
          <motion.h1
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
            className="text-4xl font-semibold tracking-tight text-balance"
          >
            Investigate the public web, <span className="text-gradient">responsibly.</span>
          </motion.h1>
          <p className="mt-4 text-muted-foreground">
            Built on free, public OSINT sources. Port scanning, breach checks, and
            other sensitive operations require explicit confirmation.
          </p>
          <div className="mt-8 font-mono text-sm text-cyan-300/80">
            <Typewriter
              words={["$ whois example.com", "$ resolve example.com → 93.184.216.34", "$ tls verify ok", "$ risk: low"]}
            />
          </div>
        </div>

        <p className="text-xs text-muted-foreground z-10">© {new Date().getFullYear()} Hello You</p>
      </div>

      {/* Right: form area */}
      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}
