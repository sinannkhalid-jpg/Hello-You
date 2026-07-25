import type { Config } from "tailwindcss";

/**
 * Monochrome enterprise design system.
 * Single dark surface, white accent, status colors only.
 */
const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: { "2xl": "1440px" },
    },
    extend: {
      colors: {
        border: "#262626",
        input: "#262626",
        ring: "#ffffff",
        background: "#090909",
        foreground: "#ffffff",
        primary: {
          DEFAULT: "#ffffff",
          foreground: "#000000",
        },
        secondary: {
          DEFAULT: "#111111",
          foreground: "#ffffff",
        },
        destructive: {
          DEFAULT: "#ef4444",
          foreground: "#ffffff",
        },
        muted: {
          DEFAULT: "#151515",
          foreground: "#a1a1aa",
        },
        accent: {
          DEFAULT: "#1a1a1a",
          foreground: "#ffffff",
        },
        popover: {
          DEFAULT: "#151515",
          foreground: "#ffffff",
        },
        card: {
          DEFAULT: "#151515",
          foreground: "#ffffff",
        },
        // Status (semantic) colors — the ONLY colored tokens
        success: { DEFAULT: "#22c55e", fg: "#16a34a" },
        warning: { DEFAULT: "#f59e0b", fg: "#d97706" },
        danger:  { DEFAULT: "#ef4444", fg: "#dc2626" },
        threat: {
          low:      "#22c55e",
          medium:   "#f59e0b",
          high:     "#f59e0b",
          critical: "#ef4444",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "fade-in": "fade-in 150ms ease-out",
        "fade-up": "fade-up 150ms ease-out",
        "accordion-down": "accordion-down 200ms ease-out",
        "accordion-up": "accordion-up 200ms ease-out",
      },
      boxShadow: {
        card: "0 1px 0 0 rgba(255,255,255,0.02) inset, 0 1px 2px rgba(0,0,0,0.4)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
