import { useTranslation } from 'react-i18next'

export default function DocumentsPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-text tracking-tight">{t('documents.title')}</h1>
          <p className="text-sm text-text-muted mt-1">{t('documents.subtitle')}</p>
        </div>
        <button className="btn btn-primary">
          {t('documents.upload')}
        </button>
      </div>

      <div className="bg-card-bg border border-border rounded-2xl p-12 text-center">
        <span className="text-4xl">📄</span>
        <p className="mt-2 text-text-muted">{t('documents.empty')}</p>
      </div>
    </div>
  )
}
