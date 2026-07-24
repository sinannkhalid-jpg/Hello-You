"use client";
import { Radar } from "@/components/effects/Radar";
import { motion } from "framer-motion";
import { Typewriter } from "@/components/effects/Typewriter";

export function LoadingScreen({ message }: { message?: string }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-background/80 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="flex flex-col items-center gap-5"
      >
        <Radar size={160} />
        <div className="text-sm text-muted-foreground">
          <Typewriter words={["Initializing…", "Connecting to intel feeds…", "Authorizing session…"]} />
        </div>
        {message && <p className="text-xs text-muted-foreground/70">{message}</p>}
      </motion.div>
    </div>
  );
}
