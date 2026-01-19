/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        identra: {
          // Near-black foundation - infrastructure palette
          bg: '#09090b',
          surface: '#0f0f11',
          'surface-elevated': '#14141a',
          'surface-hover': '#18181d',
          border: '#1f1f24',
          'border-subtle': '#17171c',
          
          // Single subtle accent - system state indicator
          primary: '#52525b',      // Neutral zinc for focus
          'primary-light': '#5a5a63',
          'primary-dark': '#3f3f46',
          
          // Status - functional only
          success: '#3a3a3a',
          warning: '#3a3a3a',
          error: '#3a3a3a',
          active: '#52525b',    // System active state
          
          // High-contrast text hierarchy
          text: {
            primary: '#fafafa',
            secondary: '#d4d4d8',
            tertiary: '#a1a1aa',
            muted: '#71717a',
            disabled: '#52525b',
          }
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.02em' }],
        'sm': ['0.8125rem', { lineHeight: '1.25rem', letterSpacing: '0.01em' }],
        'base': ['0.9375rem', { lineHeight: '1.5rem', letterSpacing: '0' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem', fontWeight: '500' }],
        'xl': ['1.375rem', { lineHeight: '1.875rem', fontWeight: '600' }],
        '2xl': ['1.75rem', { lineHeight: '2.25rem', fontWeight: '600' }],
      },
      animation: {
        'fade': 'fade 120ms ease-out',
      },
      keyframes: {
        'fade': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

