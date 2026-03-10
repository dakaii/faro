/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        risk: {
          low: "#22c55e",
          medium: "#eab308",
          high: "#ef4444",
        },
      },
    },
  },
  plugins: [],
};
