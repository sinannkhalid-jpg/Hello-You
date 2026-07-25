"use client";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  icon,
  action,
  className,
}: {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-[#262626] bg-[#151515] p-8 text-center flex flex-col items-center justify-center gap-3",
        className,
      )}
    >
      {icon && <div className="text-[#a1a1aa]">{icon}</div>}
      <h3 className="text-base font-semibold">{title}</h3>
      {description && <p className="text-sm text-[#a1a1aa] max-w-md">{description}</p>}
      {action}
    </div>
  );
}
