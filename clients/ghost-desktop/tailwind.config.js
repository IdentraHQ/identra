/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Identra brand colors from landing page
        identra: {
          bg: '#0a0a0a',
          surface: '#111111',
          border: '#222222',
          accent: '#10b981', // emerald-500
          text: {
            primary: '#f5f5f5',
            secondary: '#a3a3a3',
            muted: '#525252',
          }
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'monospace'],
      },
      animation: {
        'in': 'in 200ms ease-out',
        'fade-in': 'fade-in 200ms ease-out',
      },
      keyframes: {
        'in': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

