/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        tier: {
          free: '#6b7280',
          developer: '#3b82f6',
          pro: '#8b5cf6',
          enterprise: '#f59e0b',
        }
      }
    },
  },
  plugins: [],
}
