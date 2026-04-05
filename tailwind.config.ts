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
        background: {
          base: "#0d1117",
          card: "#161b22",
          hover: "#21262d",
        },
        border: {
          default: "#30363d",
          accent: "#238636",
        },
        text: {
          primary: "#ffffff",
          secondary: "#7d8590",
        },
        accent: {
          green: "#4ade80",
          coral: "#ff8c7a",
          blue: "#60a5fa",
        },
      },
      fontFamily: {
        "mono-display": ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
