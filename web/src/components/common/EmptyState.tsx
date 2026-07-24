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
        "glass rounded-xl p-8 text-center flex flex-col items-center justify-center gap-3",
        className,
      )}
    >
      {icon && <div className="text-cyan-300/80">{icon}</div>}
      <h3 className="text-base font-semibold">{title}</h3>
      {description && <p className="text-sm text-muted-foreground max-w-md">{description}</p>}
      {action}
    </div>
  );
}
