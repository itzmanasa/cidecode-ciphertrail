/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: "#F8FAFC", soft: "#F5F7FB", tint: "#EEF2FF" },
        primary: { DEFAULT: "#4F46E5", 50: "#EEF2FF", 100: "#E0E7FF", 500: "#4F46E5", 600: "#4338CA", 700: "#3730A3" },
        secondary: { DEFAULT: "#7C3AED", 50: "#F5F3FF", 500: "#7C3AED" },
        success: { DEFAULT: "#22C55E", 50: "#F0FDF4", 100: "#DCFCE7" },
        warning: { DEFAULT: "#F59E0B", 50: "#FFFBEB", 100: "#FEF3C7" },
        danger: { DEFAULT: "#EF4444", 50: "#FEF2F2", 100: "#FEE2E2" },
        ink: { 900: "#0F172A", 700: "#334155", 500: "#64748B", 300: "#CBD5E1", 100: "#E2E8F0" },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"], mono: ["JetBrains Mono", "ui-monospace", "monospace"] },
      borderRadius: { xl: "0.875rem", "2xl": "1.25rem" },
      boxShadow: {
        soft: "0 1px 2px rgba(15,23,42,0.04), 0 1px 8px rgba(15,23,42,0.04)",
        card: "0 1px 3px rgba(15,23,42,0.06), 0 8px 24px -8px rgba(79,70,229,0.08)",
        glow: "0 0 0 1px rgba(79,70,229,0.08), 0 8px 30px -4px rgba(79,70,229,0.18)",
      },
      backgroundImage: {
        "grad-primary": "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)",
        "grad-soft": "linear-gradient(180deg, #F8FAFC 0%, #EEF2FF 100%)",
      },
      keyframes: {
        "fade-in": { "0%": { opacity: 0, transform: "translateY(6px)" }, "100%": { opacity: 1, transform: "translateY(0)" } },
        shimmer: { "0%": { backgroundPosition: "-700px 0" }, "100%": { backgroundPosition: "700px 0" } },
      },
      animation: { "fade-in": "fade-in 0.35s ease-out both", shimmer: "shimmer 1.6s linear infinite" },
    },
  },
  plugins: [],
};
