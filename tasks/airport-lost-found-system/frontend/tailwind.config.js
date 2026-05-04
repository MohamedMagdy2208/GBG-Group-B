/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Aviation Navy + Gold palette
        navy: {
          50: "#f0f4fa",
          100: "#dbe5f3",
          200: "#b9cce8",
          300: "#8eaad5",
          400: "#6184bf",
          500: "#3f63a8",
          600: "#2e4d8d",
          700: "#243d72",
          800: "#1e3260",
          900: "#1a2a4f",
          950: "#0f1a36",
        },
        gold: {
          50: "#fff9eb",
          100: "#ffefc6",
          200: "#ffdd87",
          300: "#ffc547",
          400: "#ffb01f",
          500: "#f59e0b",
          600: "#d97706",
          700: "#b45309",
          800: "#92400e",
          900: "#78350f",
          950: "#451a03",
        },
        ink: {
          50: "#f8f9fb",
          100: "#eef0f5",
          200: "#dee1eb",
          300: "#c2c8d8",
          400: "#9ca5bb",
          500: "#71788f",
          600: "#525a72",
          700: "#3e455c",
          800: "#262d44",
          900: "#101426",
          950: "#070b1c",
        },
        // semantic states (iOS-tinted on navy palette)
        success: {
          50: "#ecfdf5",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
        },
        warn: {
          50: "#fffbeb",
          500: "#f59e0b",
          600: "#d97706",
          700: "#b45309",
        },
        danger: {
          50: "#fef2f2",
          500: "#ef4444",
          600: "#dc2626",
          700: "#b91c1c",
        },
        // legacy aliases so old code keeps compiling during the migration
        runway: "#0f1a36",
        radar: "#1a2a4f",
        sky: "#3f63a8",
        amberline: "#d97706",
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'SF Pro Text',
          'SF Pro Display',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
        display: [
          '"SF Pro Display"',
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'sans-serif',
        ],
        mono: ['"JetBrains Mono"', '"SF Mono"', 'Menlo', 'Consolas', 'monospace'],
      },
      borderRadius: {
        '4xl': '1.75rem',
      },
      boxShadow: {
        // subtle Apple-style elevation
        card: '0 1px 2px rgba(15, 26, 54, 0.04), 0 1px 1px rgba(15, 26, 54, 0.03)',
        'card-hover': '0 4px 16px rgba(15, 26, 54, 0.08), 0 2px 4px rgba(15, 26, 54, 0.04)',
        nav: '0 0 0 1px rgba(15, 26, 54, 0.04)',
        ring: '0 0 0 4px rgba(63, 99, 168, 0.2)',
        gold: '0 4px 14px rgba(245, 158, 11, 0.25)',
        navy: '0 8px 24px rgba(30, 50, 96, 0.18)',
      },
      backgroundImage: {
        'gradient-navy': 'linear-gradient(135deg, #1e3260 0%, #243d72 100%)',
        'gradient-gold': 'linear-gradient(135deg, #ffc547 0%, #f59e0b 100%)',
        'mesh-light': 'radial-gradient(at 0% 0%, rgba(63, 99, 168, 0.08) 0px, transparent 50%), radial-gradient(at 100% 0%, rgba(245, 158, 11, 0.06) 0px, transparent 50%)',
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        'apple': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: 0, transform: 'translateY(4px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        'scale-in': {
          '0%': { opacity: 0, transform: 'scale(0.96)' },
          '100%': { opacity: 1, transform: 'scale(1)' },
        },
        'slide-up': {
          '0%': { opacity: 0, transform: 'translateY(8px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        'fly-across': {
          '0%': { transform: 'translateX(-15%) translateY(20px) rotate(-8deg)' },
          '50%': { transform: 'translateX(50vw) translateY(-30px) rotate(-4deg)' },
          '100%': { transform: 'translateX(115vw) translateY(-50px) rotate(0deg)' },
        },
        'float-slow': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        'float-soft': {
          '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
          '50%': { transform: 'translateY(-8px) rotate(2deg)' },
        },
        'cloud-drift': {
          '0%': { transform: 'translateX(0) translateY(0)' },
          '100%': { transform: 'translateX(100vw) translateY(-10px)' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.8)', opacity: 0.8 },
          '100%': { transform: 'scale(2.4)', opacity: 0 },
        },
        'orbit': {
          '0%': { transform: 'rotate(0deg) translateX(120px) rotate(0deg)' },
          '100%': { transform: 'rotate(360deg) translateX(120px) rotate(-360deg)' },
        },
        'gradient-shift': {
          '0%, 100%': { 'background-position': '0% 50%' },
          '50%': { 'background-position': '100% 50%' },
        },
        'typing-bubble': {
          '0%, 60%, 100%': { transform: 'translateY(0)', opacity: 0.4 },
          '30%': { transform: 'translateY(-4px)', opacity: 1 },
        },
        'message-in': {
          '0%': { opacity: 0, transform: 'translateY(10px) scale(0.95)' },
          '100%': { opacity: 1, transform: 'translateY(0) scale(1)' },
        },
        'count-up': {
          '0%': { transform: 'translateY(8px)', opacity: 0 },
          '100%': { transform: 'translateY(0)', opacity: 1 },
        },
        'shimmer': {
          '0%': { 'background-position': '-200% 0' },
          '100%': { 'background-position': '200% 0' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.2s ease-out',
        'scale-in': 'scale-in 0.18s ease-out',
        'slide-up': 'slide-up 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        'fly-across': 'fly-across 18s linear infinite',
        'float-slow': 'float-slow 6s ease-in-out infinite',
        'float-soft': 'float-soft 4s ease-in-out infinite',
        'cloud-drift': 'cloud-drift 60s linear infinite',
        'pulse-ring': 'pulse-ring 2.4s cubic-bezier(0, 0, 0.2, 1) infinite',
        'orbit': 'orbit 20s linear infinite',
        'gradient-shift': 'gradient-shift 8s ease infinite',
        'typing-bubble': 'typing-bubble 1.4s ease-in-out infinite',
        'message-in': 'message-in 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)',
        'count-up': 'count-up 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
        'shimmer': 'shimmer 3s linear infinite',
      },
    },
  },
  plugins: [],
};
