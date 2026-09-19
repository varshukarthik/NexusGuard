/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        // NovaTech Solutions brand blue (deep, trustworthy enterprise blue) + navy ink
        brand: {
          50: "#eff5ff", 100: "#dbe8fe", 200: "#bfd5fe", 300: "#93b7fd", 400: "#6090fa",
          500: "#3b6cf6", 600: "#2552eb", 700: "#1d40d8", 800: "#1e36af", 900: "#1e338a", 950: "#172154",
        },
        ink: { 900: "#0b1220", 800: "#111a2e", 700: "#1a2540" },
      },
      boxShadow: { card: "0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06)" },
      keyframes: {
        "fade-in": { from: { opacity: 0, transform: "translateY(4px)" }, to: { opacity: 1, transform: "none" } },
        "rise": { from: { opacity: 0, transform: "translateY(10px)" }, to: { opacity: 1, transform: "none" } },
        "bar": { "0%": { transform: "translateX(-100%)" }, "100%": { transform: "translateX(260%)" } },
        "blink": { "0%, 100%": { opacity: 0.25 }, "50%": { opacity: 1 } },
      },
      animation: { "fade-in": "fade-in .25s ease-out both", rise: "rise .45s cubic-bezier(.2,.7,.2,1) both",
                   bar: "bar 1.3s ease-in-out infinite", blink: "blink 1.2s ease-in-out infinite" },
    },
  },
  plugins: [],
};
