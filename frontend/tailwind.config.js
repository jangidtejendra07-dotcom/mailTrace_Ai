/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          950: "#05080c",
          900: "#0a0f16",
          800: "#111820",
          700: "#1a232e",
          600: "#26313f",
        },
        signal: {
          safe: "#2dd4a7",
          watch: "#f5b942",
          danger: "#ff5d5d",
          critical: "#ff2d55",
        },
        trace: "#3ddc97",
        wire: "#7c9cff",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
        body: ["'Inter'", "sans-serif"],
      },
      backgroundImage: {
        grid: "linear-gradient(rgba(61,220,151,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(61,220,151,0.06) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "28px 28px",
      },
    },
  },
  plugins: [],
}
