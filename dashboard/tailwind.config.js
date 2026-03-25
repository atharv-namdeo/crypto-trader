/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': 'var(--bg-primary)',
        'bg-secondary': 'var(--bg-secondary)',
        'bg-tertiary': 'var(--bg-tertiary)',
        'bg-hover': 'var(--bg-hover)',
        'border': 'var(--border)',
        'border-bright': 'var(--border-bright)',
        'accent-primary': 'var(--accent-primary)',
        'accent-success': 'var(--accent-success)',
        'accent-danger': 'var(--accent-danger)',
        'accent-warning': 'var(--accent-warning)',
        'accent-purple': 'var(--accent-purple)',
        'accent-cyan': 'var(--accent-cyan)',
        'accent-orange': 'var(--accent-orange)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-tertiary': 'var(--text-tertiary)',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fade-in 0.3s ease-out forwards',
        'pulse-subtle': 'pulse-subtle 2s infinite ease-in-out',
      },
    },
  },
  plugins: [],
}
