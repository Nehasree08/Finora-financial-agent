/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#070b14",
          900: "#0b1220",
          800: "#121a2b",
          700: "#1a2438",
        },
        gold: {
          400: "#e0c36a",
          500: "#c9a227",
          600: "#a9851c",
        },
        aqua: {
          300: "#7ee7d8",
          400: "#2dd4bf",
          500: "#14b8a6",
        },
      },
      fontFamily: {
        display: ["Syne", "sans-serif"],
        sans: ["Manrope", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 80px rgba(201, 162, 39, 0.12)",
      },
    },
  },
  plugins: [],
};
