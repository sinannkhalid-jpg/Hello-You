"use client";
import { motion } from "framer-motion";
import { Typewriter } from "@/components/effects/Typewriter";

export function LoadingScreen({ message }: { message?: string }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[#090909]">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="flex flex-col items-center gap-5"
      >
        <div className="h-10 w-10 rounded-full border border-[#262626] border-t-white animate-spin" />
        <div className="text-sm text-[#a1a1aa]">
          <Typewriter words={["Initializing…", "Connecting to intel feeds…", "Authorizing session…"]} />
        </div>
        {message && <p className="text-xs text-[#71717a]">{message}</p>}
      </motion.div>
    </div>
  );
}
