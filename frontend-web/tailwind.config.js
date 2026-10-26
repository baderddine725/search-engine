/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        ink: {
          50:  '#f6f7fb',
          100: '#eef0f6',
          200: '#dde2ec',
          300: '#bdc4d4',
          400: '#8e97af',
          500: '#5e6882',
          600: '#404a63',
          700: '#2e3650',
          800: '#1b2238',
          900: '#0b1024',
        },
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
        violet: '#8b5cf6',
        cyan: '#06b6d4',
      },
      boxShadow: {
        card: '0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.03)',
        'card-hover': '0 4px 24px -8px rgba(79,70,229,.18), 0 2px 6px rgba(16,24,40,.05)',
      },
      backgroundImage: {
        'grid-slate': 'linear-gradient(to right, rgba(99,102,241,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(99,102,241,0.06) 1px, transparent 1px)',
      },
    },
  },
  plugins: [],
};
