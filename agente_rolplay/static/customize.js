// Shared dashboard customization loader (DB-backed, per-user)
(function () {
  const CACHE_KEY = 'sb-customize-cache';
  const TOKEN_KEY = 'access_token';
  const THEME_KEY = 'sb-theme';
  const DEFAULTS = {
    primary_color: '#dc2626',
    secondary_color: '#991b1b',
    tertiary_color: '#fca5a5',
    font_family: 'inter',
    font_scale: 'medium',
    theme_mode: 'dark',
    language: 'es',
  };

  const FONT_FAMILY_MAP = {
    inter: "'Inter', -apple-system, sans-serif",
    poppins: "'Poppins', -apple-system, sans-serif",
    manrope: "'Manrope', -apple-system, sans-serif",
    source_sans_3: "'Source Sans 3', -apple-system, sans-serif",
  };

  const FONT_SCALE_MAP = {
    small: '15px',
    medium: '16px',
    large: '17px',
  };

  const HEX_COLOR_RE = /^#[0-9A-Fa-f]{6}$/;
  let current = { ...DEFAULTS };

  function isValidHex(value) {
    return typeof value === 'string' && HEX_COLOR_RE.test(value.trim());
  }

  function clampChoice(value, allowed, fallback) {
    return allowed.includes(value) ? value : fallback;
  }

  function hexToRgb(hex) {
    const clean = hex.replace('#', '');
    const intVal = Number.parseInt(clean, 16);
    return {
      r: (intVal >> 16) & 255,
      g: (intVal >> 8) & 255,
      b: intVal & 255,
    };
  }

  function alpha(hex, a) {
    const rgb = hexToRgb(hex);
    return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${a})`;
  }

  function normalize(input) {
    const candidate = input && typeof input === 'object' ? input : {};
    return {
      primary_color: isValidHex(candidate.primary_color)
        ? candidate.primary_color
        : DEFAULTS.primary_color,
      secondary_color: isValidHex(candidate.secondary_color)
        ? candidate.secondary_color
        : DEFAULTS.secondary_color,
      tertiary_color: isValidHex(candidate.tertiary_color)
        ? candidate.tertiary_color
        : DEFAULTS.tertiary_color,
      font_family: clampChoice(
        String(candidate.font_family || ''),
        Object.keys(FONT_FAMILY_MAP),
        DEFAULTS.font_family,
      ),
      font_scale: clampChoice(
        String(candidate.font_scale || ''),
        Object.keys(FONT_SCALE_MAP),
        DEFAULTS.font_scale,
      ),
      theme_mode: clampChoice(
        String(candidate.theme_mode || ''),
        ['dark', 'light'],
        DEFAULTS.theme_mode,
      ),
      language: clampChoice(
        String(candidate.language || ''),
        ['es', 'en'],
        DEFAULTS.language,
      ),
    };
  }

  function applyTheme(mode) {
    const html = document.documentElement;
    if (html.getAttribute('data-theme') === mode) {
      localStorage.setItem(THEME_KEY, mode);
      return;
    }

    if (typeof window.applyTheme === 'function') {
      window.applyTheme(mode);
      return;
    }

    html.setAttribute('data-theme', mode);
    localStorage.setItem(THEME_KEY, mode);

    const btn = document.getElementById('themeBtn');
    if (btn) {
      btn.textContent = mode === 'dark' ? '☀️' : '🌙';
      btn.setAttribute(
        'aria-label',
        mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode',
      );
    }
  }

  function applyLanguage(language) {
    if (typeof window.getLang === 'function' && window.getLang() === language) {
      localStorage.setItem('sb-lang', language);
      return;
    }
    if (typeof window.setLang === 'function') {
      window.setLang(language);
    } else {
      localStorage.setItem('sb-lang', language);
    }
  }

  function applyStyles(pref) {
    const root = document.documentElement;

    root.style.setProperty('--indigo', pref.primary_color);
    root.style.setProperty('--violet', pref.secondary_color);
    root.style.setProperty('--accent-tertiary', pref.tertiary_color);
    root.style.setProperty('--border-hover', alpha(pref.primary_color, 0.35));
    root.style.setProperty('--sidebar-active', alpha(pref.primary_color, 0.15));
    root.style.setProperty('--sidebar-active-border', pref.primary_color);
    root.style.setProperty('--badge-inactive-color', pref.primary_color);
    root.style.setProperty('--badge-inactive-bg', alpha(pref.primary_color, 0.12));
    root.style.setProperty('--app-font-family', FONT_FAMILY_MAP[pref.font_family]);

    root.style.setProperty('--font-scale', pref.font_scale);
    root.style.fontSize = FONT_SCALE_MAP[pref.font_scale];

    applyTheme(pref.theme_mode);
    applyLanguage(pref.language);
  }

  function applyCustomization(input, opts) {
    const options = opts || {};
    const normalized = normalize(input);

    current = { ...normalized };
    applyStyles(normalized);

    if (options.persistCache !== false) {
      localStorage.setItem(CACHE_KEY, JSON.stringify(normalized));
    }

    document.dispatchEvent(
      new CustomEvent('customization:applied', { detail: { customization: { ...current } } }),
    );

    return { ...current };
  }

  function getCurrent() {
    return { ...current };
  }

  async function loadCustomization() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      return getCurrent();
    }

    const res = await fetch('/api/users/customization', {
      headers: { Authorization: 'Bearer ' + token },
    });
    if (!res.ok) {
      return getCurrent();
    }

    const data = await res.json();
    return applyCustomization(data, { persistCache: true });
  }

  function tryApplyCache() {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) {
      return;
    }
    try {
      const parsed = JSON.parse(raw);
      applyCustomization(parsed, { persistCache: false });
    } catch (_) {
      // Ignore malformed cache and continue with defaults.
    }
  }

  window.customizeSettings = {
    defaults: { ...DEFAULTS },
    getCurrent,
    applyCustomization,
    loadCustomization,
  };

  function init() {
    tryApplyCache();
    loadCustomization().catch(() => {
      // Keep page functional even if customization fetch fails.
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
