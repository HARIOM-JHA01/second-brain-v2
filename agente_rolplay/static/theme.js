// Shared theme toggle — included by all pages
(function () {
  const STORAGE_KEY = 'sb-theme';
  const html = document.documentElement;

  function applyTheme(theme) {
    html.setAttribute('data-theme', theme);
    const btn = document.getElementById('themeBtn');
    if (btn) {
      btn.textContent = theme === 'dark' ? '☀️' : '🌙';
      btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    }
    localStorage.setItem(STORAGE_KEY, theme);
  }

  window.applyTheme = applyTheme;

  // Expose globally so onclick handlers work
  window.toggleTheme = function () {
    applyTheme(html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  };

  // Apply immediately to avoid flash
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    applyTheme(saved);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    applyTheme('light');
  } else {
    applyTheme('dark');
  }
})();
