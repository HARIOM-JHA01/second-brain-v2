import { useTranslation } from 'react-i18next'

export default function SettingsPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-text tracking-tight">{t('settings.title')}</h1>
        <p className="text-sm text-text-muted mt-1">{t('settings.subtitle')}</p>
      </div>

      <div className="bg-card-bg border border-border rounded-2xl p-6">
        <h2 className="text-sm font-bold text-text mb-4">{t('settings.sections.profile')}</h2>
        <p className="text-text-muted text-sm">Coming soon</p>
      </div>
    </div>
  )
}
