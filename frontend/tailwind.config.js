/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      screens: {
        'desk': '920px',
      },
      colors: {
        // Accent / interactive colour
        primary: {
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          900: '#312e81',
        },
        // Dark-theme surface palette
        surface: {
          950: '#09090f',  // page background
          900: '#111118',  // card
          800: '#1c1c27',  // elevated card / input bg
          700: '#2a2a3a',  // border
          600: '#3a3a4e',  // muted border / divider
        },
      },
    },
  },
  plugins: [],
}
