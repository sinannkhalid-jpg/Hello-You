"use client";
import { Toaster as SonnerToaster } from "sonner";
export function Toaster() {
  return (
    <SonnerToaster
      theme="dark"
      position="top-right"
      toastOptions={{
        style: {
          background: "#151515",
          border: "1px solid #262626",
          color: "#ffffff",
        },
      }}
    />
  );
}
