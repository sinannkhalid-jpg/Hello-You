"use client";
/** A small spinning radar/sweep used on the auth loading screen. */
import { motion } from "framer-motion";

export function Radar({ size = 180 }: { size?: number }) {
  return (
    <div
      className="relative grid place-items-center"
      style={{ width: size, height: size }}
      role="status"
      aria-label="Loading"
    >
      <div className="absolute inset-0 rounded-full border border-cyan-400/20" />
      <div className="absolute inset-3 rounded-full border border-cyan-400/20" />
      <div className="absolute inset-6 rounded-full border border-cyan-400/20" />
      <div className="absolute inset-9 rounded-full border border-cyan-400/10" />
      <div className="absolute left-1/2 top-1/2 h-px w-1/2 -translate-y-1/2 origin-left bg-gradient-to-r from-cyan-400/70 to-transparent animate-radar-spin" />
      <div className="absolute left-1/2 top-1/2 h-1/2 w-px -translate-x-1/2 origin-top bg-gradient-to-b from-violet-400/40 to-transparent animate-radar-spin [animation-direction:reverse]" />
      <motion.div
        className="absolute h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_18px_4px_rgba(0,240,255,0.7)]"
        animate={{ scale: [1, 1.4, 1] }}
        transition={{ repeat: Infinity, duration: 1.6 }}
      />
    </div>
  );
}
