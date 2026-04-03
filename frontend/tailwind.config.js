/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: '#06b6d4',
        dark: {
          900: '#050508',
          800: '#0a0a12',
          700: '#0f0f1a',
          600: '#1a1a2e',
          500: '#252540',
        },
        neon: {
          green:  '#00ff88',
          amber:  '#ffaa00',
          red:    '#ff2244',
          purple: '#aa44ff',
          cyan:   '#06b6d4',
        },
        project: {
          clippack: '#ff8d89',
          trendkr:  '#06b6d4',
          studio:   '#aa44ff',
          dubber:   '#ffaa00',
        },
      },
      fontFamily: {
        game: ['Rajdhani', 'system-ui', 'sans-serif'],
        vn:   ['Be Vietnam Pro', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow':    'pulse 3s ease-in-out infinite',
        'radar-sweep':   'radarSweep 4s linear infinite',
        'warning-flash': 'warningFlash 1s ease-in-out infinite',
        'fade-in-up':    'fadeInUp 0.4s ease-out forwards',
      },
      keyframes: {
        radarSweep: {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        warningFlash: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.3' },
        },
        fadeInUp: {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
