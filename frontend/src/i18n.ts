import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import es from './locales/es.json'
import en from './locales/en.json'

const savedLang = localStorage.getItem('sb-lang') || 'es'

i18n
  .use(initReactI18next)
  .init({
    resources: {
      es: { translation: es },
      en: { translation: en },
    },
    lng: savedLang,
    fallbackLng: 'es',
    interpolation: {
      escapeValue: false,
    },
  })

export function changeLanguage(lang: 'es' | 'en') {
  localStorage.setItem('sb-lang', lang)
  i18n.changeLanguage(lang)
  document.dispatchEvent(new Event('langchange'))
}

export function getCurrentLanguage(): 'es' | 'en' {
  return (localStorage.getItem('sb-lang') as 'es' | 'en') || 'es'
}

export default i18n
