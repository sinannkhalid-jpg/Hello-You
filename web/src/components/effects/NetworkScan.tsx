"use client";
/**
 * Network scan animation used on the dashboard hero and loading states.
 * Streams faux log lines; decorative only.
 */
import { useEffect, useState } from "react";

const FAKE = [
  "scanning dns records…",
  "resolved 12 hostnames",
  "fetching SSL certificate…",
  "verified TLS chain",
  "querying RDAP registry…",
  "enumerating subdomains via CT logs…",
  "matching 47 technology signatures",
  "computing risk score",
  "building relationship graph",
  "summarizing findings",
];

export function NetworkScan() {
  const [lines, setLines] = useState<string[]>([]);
  useEffect(() => {
    let i = 0;
    const id = setInterval(() => {
      setLines((p) => {
        const next = [...p, `[${new Date().toISOString().slice(11, 19)}] ${FAKE[i % FAKE.length]}`];
        return next.slice(-6);
      });
      i++;
    }, 700);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="rounded-lg border border-cyan-400/15 bg-black/40 p-3 font-mono text-xs text-cyan-200/80 scan-overlay">
      {lines.map((l, idx) => (
        <div key={idx} className="truncate">{l}</div>
      ))}
      <div className="mt-1 text-cyan-300/70">▌</div>
    </div>
  );
}
