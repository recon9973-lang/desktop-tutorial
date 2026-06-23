import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#2563EB",
          dark: "#1D4ED8",
          light: "#EFF6FF",
        },
        navy: {
          DEFAULT: "#0A1628",
          light: "#1A3A6B",
        },
        accent: "#06B6D4",
      },
      fontFamily: {
        sans: ["var(--font-noto)", "sans-serif"],
      },
      backgroundImage: {
        "gradient-hero": "linear-gradient(135deg, #0A1628 0%, #1A3A6B 55%, #1e40af 100%)",
        "gradient-ai": "linear-gradient(135deg, #0A1628 0%, #0e4f7a 50%, #0891b2 100%)",
        "gradient-cta": "linear-gradient(90deg, #2563EB 0%, #1D4ED8 100%)",
        "gradient-badge": "linear-gradient(90deg, #06B6D4, #2563EB)",
      },
      animation: {
        "fade-up": "fadeUp 0.6s ease forwards",
        "count-up": "fadeIn 1.5s ease forwards",
        "pulse-ring": "pulseRing 2.5s infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        pulseRing: {
          "0%": { boxShadow: "0 0 0 0 rgba(37,99,235,0.5)" },
          "70%": { boxShadow: "0 0 0 12px rgba(37,99,235,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(37,99,235,0)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
