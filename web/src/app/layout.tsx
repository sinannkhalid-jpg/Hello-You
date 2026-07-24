import "./../styles/globals.css";
import type { Metadata, Viewport } from "next";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Hello You — Cyber Intelligence Platform",
  description:
    "Educational OSINT platform for authorized investigations and cybersecurity research. Built on publicly available data only.",
  applicationName: "Hello You",
  keywords: ["OSINT", "cybersecurity", "threat intelligence", "investigation", "education"],
  authors: [{ name: "Hello You" }],
};

export const viewport: Viewport = {
  themeColor: "#020617",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
