import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg:    "#0b1020",
        panel: "#111934",
        panel2:"#182146",
        ink:   "#e6ebff",
        muted: "#8c97c2",
        line:  "#233063",
        accent:"#7c9cff",
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", "Inter", "SF Pro Text", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
