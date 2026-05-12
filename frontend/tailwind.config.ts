import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        clay: {
          50: "#fdf6f0",
          100: "#f5e6d6",
          200: "#e8c9a8",
          300: "#d4a373",
          400: "#c08050",
          500: "#a0663a",
          600: "#804d2a",
          700: "#603820",
          800: "#402818",
          900: "#2a1a10",
        },
        celadon: {
          50: "#f0f5f0",
          100: "#d8e8d5",
          200: "#b5d1ab",
          300: "#8fb882",
          400: "#6a9f5a",
          500: "#4d8040",
          600: "#3a6330",
          700: "#2a4822",
          800: "#1c3018",
          900: "#101c0e",
        },
        ink: {
          50: "#f5f5f5",
          100: "#e0e0e0",
          200: "#b0b0b0",
          300: "#808080",
          400: "#505050",
          500: "#303030",
          600: "#222222",
          700: "#1a1a1a",
          800: "#111111",
          900: "#0a0a0a",
        },
      },
      fontFamily: {
        display: ['"Noto Serif SC"', "serif"],
        body: ['"Noto Sans SC"', "sans-serif"],
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
export default config;
