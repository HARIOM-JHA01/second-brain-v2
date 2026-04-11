import { useTranslation } from 'react-i18next'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/contexts/ThemeContext'
import { changeLanguage, getCurrentLanguage } from '@/i18n'

export function Navbar() {
  const { t } = useTranslation()
  const { theme, toggleTheme } = useTheme()
  const currentLang = getCurrentLanguage()

  const handleLanguageChange = (lang: 'es' | 'en') => {
    changeLanguage(lang)
  }

  return (
    <nav className="sticky top-0 z-20 flex items-center justify-between px-8 py-4 border-b border-border bg-navbar-bg backdrop-blur-xl transition-colors duration-300">
      <div className="flex items-center gap-4">
        <a href="/app/dashboard" className="flex items-center">
          <img 
            src="/static/second-brain-logo.png" 
            alt="Second Brain" 
            className="h-11 max-w-[140px] object-contain"
          />
        </a>
        <div className="w-px h-6 bg-border" />
        <a 
          href="https://www.rolplay.ai/" 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center gap-1 opacity-75 hover:opacity-100 transition-opacity"
        >
          <span className="text-[10px] font-medium text-text-muted tracking-wider uppercase">
            {t('nav.by')}
          </span>
          <img 
            src="/static/rolplay-logo.png" 
            alt="Rolplay" 
            className="h-7 object-contain"
          />
        </a>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center bg-toggle-bg border border-border rounded-lg p-0.5 gap-0.5">
          <button
            onClick={() => handleLanguageChange('es')}
            className={`px-2 py-1 rounded-md text-[11px] font-bold tracking-wider transition-all ${
              currentLang === 'es'
                ? 'bg-primary text-white'
                : 'text-text-muted hover:text-text'
            }`}
          >
            ES
          </button>
          <button
            onClick={() => handleLanguageChange('en')}
            className={`px-2 py-1 rounded-md text-[11px] font-bold tracking-wider transition-all ${
              currentLang === 'en'
                ? 'bg-primary text-white'
                : 'text-text-muted hover:text-text'
            }`}
          >
            EN
          </button>
        </div>

        <button
          onClick={toggleTheme}
          className="w-8 h-8 rounded-lg bg-toggle-bg border border-border flex items-center justify-center hover:bg-surface-hover transition-all"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4 text-text-dim" />
          ) : (
            <Moon className="h-4 w-4 text-text-dim" />
          )}
        </button>
      </div>
    </nav>
  )
}
