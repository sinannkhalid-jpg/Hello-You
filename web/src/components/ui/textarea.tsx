"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "flex min-h-[80px] w-full rounded-md border border-[#262626] bg-[#0f0f0f] px-3 py-2 text-sm text-white",
      "placeholder:text-[#71717a]",
      "focus:outline-none focus:border-white",
      "disabled:cursor-not-allowed disabled:opacity-50",
      "transition-colors duration-150",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";
export { Textarea };
