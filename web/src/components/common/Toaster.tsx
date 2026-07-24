"use client";
import { Toaster as SonnerToaster } from "sonner";
export function Toaster() {
  return (
    <SonnerToaster
      theme="dark"
      position="top-right"
      toastOptions={{
        style: {
          background: "rgba(15, 23, 42, 0.85)",
          border: "1px solid rgba(255,255,255,0.08)",
          color: "#e2e8f0",
          backdropFilter: "blur(12px)",
        },
      }}
    />
  );
}
