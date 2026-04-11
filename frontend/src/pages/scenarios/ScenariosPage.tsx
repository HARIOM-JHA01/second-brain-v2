import { useTranslation } from 'react-i18next'

export default function ScenariosPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-text tracking-tight">{t('scenarios.title')}</h1>
        <p className="text-sm text-text-muted mt-1">{t('scenarios.subtitle')}</p>
      </div>

      <div className="bg-card-bg border border-border rounded-2xl p-12 text-center">
        <span className="text-4xl">🎯</span>
        <p className="mt-2 text-text-muted">Coming soon</p>
      </div>
    </div>
  )
}
