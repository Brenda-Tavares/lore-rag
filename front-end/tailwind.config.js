import typography from '@tailwindcss/typography';

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Instrument Serif"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        ink: {
          950: '#0B0E14',
          900: '#11151C',
          800: '#161B24',
          700: '#1F2430',
          600: '#2A3040',
        },
        accent: {
          DEFAULT: '#5EEAD4',
          dim: '#2DD4BF',
        },
      },
    },
  },
  plugins: [typography],
}