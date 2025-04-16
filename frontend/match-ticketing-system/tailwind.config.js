/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}", // 👈 this watches all your React files
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}