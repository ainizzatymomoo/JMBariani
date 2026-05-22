/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fef7ed',
          100: '#fdedd4',
          200: '#fad7a8',
          300: '#f6ba71',
          400: '#f19338',
          500: '#ee7b15',
          600: '#df610b',
          700: '#b9490b',
          800: '#933a10',
          900: '#773110',
        },
        brand: {
          dark: '#1a1a2e',
          mid: '#16213e',
          accent: '#e94560',
        }
      }
    },
  },
  plugins: [],
}
