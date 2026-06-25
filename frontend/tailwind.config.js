/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Token-Farben — RGB-Kanäle aus index.css; ermöglichen Opazitäten (bg-brand/10).
        bg: "rgb(var(--bg) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        "surface-2": "rgb(var(--surface-2) / <alpha-value>)",
        ink: "rgb(var(--ink) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)",
        brand: {
          DEFAULT: "rgb(var(--brand) / <alpha-value>)",
          strong: "rgb(var(--brand-strong) / <alpha-value>)",
          ink: "rgb(var(--brand-ink) / <alpha-value>)",
        },
        bull: "rgb(var(--bull) / <alpha-value>)",
        bear: "rgb(var(--bear) / <alpha-value>)",
        neutral: "rgb(var(--neutral) / <alpha-value>)",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(16,22,38,.05), 0 10px 30px -16px rgba(16,22,38,.22)",
      },
      borderRadius: {
        panel: "14px",
      },
    },
  },
  plugins: [],
};
