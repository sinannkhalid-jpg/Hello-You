"use client";
import { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function KeyValue({ items, columns = 2 }: { items: { label: string; value: ReactNode; mono?: boolean; copy?: string }[]; columns?: 1 | 2 | 3 | 4 }) {
  const colCls = {
    1: "grid-cols-1",
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  }[columns];
  return (
    <dl className={cn("grid gap-3", colCls)}>
      {items.map((it, i) => (
        <div key={i} className="rounded-md border border-white/5 bg-white/5 p-3">
          <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">{it.label}</dt>
          <dd className={cn("mt-1 text-sm break-words", it.mono && "font-mono")}>
            {it.value ?? <span className="text-muted-foreground">—</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function CodeBlock({ value, language }: { value: any; language?: string }) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return (
    <pre className="rounded-md border border-white/10 bg-black/40 p-3 text-xs font-mono overflow-x-auto max-h-[420px]">
      <code>{text}</code>
    </pre>
  );
}
