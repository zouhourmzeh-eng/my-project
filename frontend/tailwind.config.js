/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f1f5fb",
          100: "#dde8f5",
          500: "#1f4e8f",
          600: "#163e76",
          700: "#0f2f5e",
        },
      },
    },
  },
  plugins: [],
};
