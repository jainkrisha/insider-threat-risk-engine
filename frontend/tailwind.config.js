/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['Inter', 'sans-serif'] },
      colors: {
        glass: 'rgba(30,41,59,0.7)',
      },
      backdropBlur: { glass: '12px' },
      boxShadow: {
        'glow-purple': '0 0 40px -10px rgba(168, 85, 247, 0.4)',
        'glow-cyan': '0 0 40px -10px rgba(6, 182, 212, 0.4)',
        'glow-indigo': '0 0 40px -10px rgba(99, 102, 241, 0.4)',
        'glow-blue': '0 0 40px -10px rgba(59, 130, 246, 0.4)',
        'glow-emerald': '0 0 40px -10px rgba(16, 185, 129, 0.4)',
        'glow-red': '0 0 40px -10px rgba(239, 68, 68, 0.4)',
        'glow-green': '0 0 40px -10px rgba(34, 197, 94, 0.4)',
        'glow-teal': '0 0 40px -10px rgba(146, 64, 45, 0.35)',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.35s ease-out',
        pulse2: 'pulse 2s cubic-bezier(0.4,0,0.6,1) infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(16px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
