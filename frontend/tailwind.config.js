/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#dc2626',
        secondary: '#991b1b',
        background: {
          DEFAULT: 'var(--bg)',
          alt: 'var(--bg-alt)',
        },
        surface: 'var(--surface)',
        border: 'var(--border)',
        'border-hover': 'var(--border-hover)',
        text: {
          DEFAULT: 'var(--text)',
          dim: 'var(--text-dim)',
          muted: 'var(--text-muted)',
        },
        'input-bg': 'var(--input-bg)',
        'input-color': 'var(--input-color)',
        placeholder: 'var(--placeholder)',
        'card-bg': 'var(--card-bg)',
        'table-header': 'var(--table-header)',
        'table-row-hover': 'var(--table-row-hover)',
        'table-border': 'var(--table-border)',
        'modal-bg': 'var(--modal-bg)',
        'modal-overlay': 'var(--modal-overlay)',
        'badge-active-bg': 'var(--badge-active-bg)',
        'badge-active-color': 'var(--badge-active-color)',
        'badge-inactive-bg': 'var(--badge-inactive-bg)',
        'badge-inactive-color': 'var(--badge-inactive-color)',
        'toggle-bg': 'var(--toggle-bg)',
        error: 'var(--error)',
        success: 'var(--success)',
        'sidebar-active': 'var(--sidebar-active)',
        'sidebar-active-border': 'var(--sidebar-active-border)',
        'navbar-bg': 'var(--navbar-bg)',
        'sidebar-bg': 'var(--sidebar-bg)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
