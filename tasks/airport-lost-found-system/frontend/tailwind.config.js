/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        runway: "#111827",
        radar: "#0f766e",
        sky: "#2563eb",
        amberline: "#d97706"
      }
    },
  },
  plugins: [],
};
