import { useState, useEffect, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/contexts/ThemeContext'
import { changeLanguage, getCurrentLanguage } from '@/i18n'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Alert } from '@/components/ui/Alert'
import { signup as apiSignup } from '@/api/auth'

export default function AuthPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { login, isAuthenticated } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const currentLang = getCurrentLanguage()
  
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    fullName: '',
    jobTitle: '',
    whatsapp: '',
    organization: '',
  })

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/app/dashboard')
    }
  }, [isAuthenticated, navigate])

  const handleLanguageChange = (lang: 'es' | 'en') => {
    changeLanguage(lang)
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      if (mode === 'login') {
        await login(formData.email, formData.password)
        navigate('/app/dashboard')
      } else {
        await apiSignup({
          email: formData.email,
          password: formData.password,
          full_name: formData.fullName,
          job_title: formData.jobTitle,
          whatsapp_number: formData.whatsapp,
          organization_name: formData.organization,
        })
        await login(formData.email, formData.password)
        navigate('/app/dashboard')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('common.error'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg)' }}>
      <a href="/" className="fixed top-5 left-6 z-30 flex items-center gap-2 text-text-dim hover:text-text text-sm font-semibold transition-colors">
        ← {t('auth.back')}
      </a>

      <div className="fixed top-4 right-6 z-30 flex items-center gap-3">
        <div className="flex items-center bg-toggle-bg border border-border rounded-lg p-0.5 gap-0.5">
          <button
            onClick={() => handleLanguageChange('es')}
            className={`px-2 py-1 rounded-md text-[11px] font-bold tracking-wider transition-all ${
              currentLang === 'es' ? 'bg-primary text-white' : 'text-text-muted hover:text-text'
            }`}
          >
            ES
          </button>
          <button
            onClick={() => handleLanguageChange('en')}
            className={`px-2 py-1 rounded-md text-[11px] font-bold tracking-wider transition-all ${
              currentLang === 'en' ? 'bg-primary text-white' : 'text-text-muted hover:text-text'
            }`}
          >
            EN
          </button>
        </div>
        <button
          onClick={toggleTheme}
          className="w-9 h-9 rounded-lg bg-toggle-bg border border-border flex items-center justify-center hover:bg-surface-hover transition-all"
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </div>

      <div className="flex min-h-screen">
        <div className="hidden lg:flex lg:w-2/5 relative overflow-hidden">
          <img
            src={`https://picsum.photos/seed/sb-${mode}/900/1200`}
            alt=""
            className="absolute inset-0 w-full h-full object-cover"
          />
          <div 
            className="absolute inset-0"
            style={{
              background: 'linear-gradient(160deg, rgba(6,6,20,.6) 0%, rgba(220,38,38,.25) 100%)'
            }}
          />
          <div className="relative z-10 flex flex-col justify-between p-10 w-full">
            <div className="flex items-center gap-3">
              <img src="/static/second-brain-logo.png" alt="Second Brain" className="h-10 brightness-0 invert" />
              <div className="w-px h-4 bg-white/25" />
              <a href="https://www.rolplay.ai/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 opacity-80 hover:opacity-100">
                <span className="text-xs text-white/60 uppercase tracking-wider">{t('brand.by')}</span>
                <img src="/static/rolplay-logo.png" alt="Rolplay" className="h-5 brightness-0 invert" />
              </a>
            </div>
            <p 
              className="text-white/85 text-lg font-semibold leading-relaxed"
              dangerouslySetInnerHTML={{ 
                __html: mode === 'login' ? t('auth.quote.login') : t('auth.quote.signup')
              }}
            />
          </div>
        </div>

        <div className="flex-1 flex items-center justify-center p-8">
          <div className="w-full max-w-md">
            <div className="text-center mb-8">
              <div className="flex items-center justify-center gap-3 mb-6">
                <img src="/static/second-brain-logo.png" alt="Second Brain" className="h-11" />
                <div className="w-px h-6 bg-border" />
                <a href="https://www.rolplay.ai/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 opacity-70 hover:opacity-100">
                  <span className="text-xs text-text-muted uppercase tracking-wider">{t('brand.by')}</span>
                  <img src="/static/rolplay-logo.png" alt="Rolplay" className="h-7" />
                </a>
              </div>
              <h1 className="text-3xl font-black text-text tracking-tight mb-2">
                {mode === 'login' ? t('auth.login.heading') : t('auth.signup.heading')}
              </h1>
              <p className="text-text-muted">
                {mode === 'login' ? t('auth.login.subtitle') : t('auth.signup.subtitle')}
              </p>
            </div>

            {error && <Alert variant="error" className="mb-4">{error}</Alert>}

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === 'signup' && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      label={t('auth.signup.fullname')}
                      placeholder={t('auth.signup.fullname_ph')}
                      required
                      value={formData.fullName}
                      onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                    />
                    <Input
                      label={t('auth.signup.jobtitle')}
                      placeholder={t('auth.signup.jobtitle_ph')}
                      required
                      value={formData.jobTitle}
                      onChange={(e) => setFormData({ ...formData, jobTitle: e.target.value })}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      label={t('auth.signup.email')}
                      type="email"
                      placeholder={t('auth.signup.email_ph')}
                      required
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    />
                    <Input
                      label={t('auth.signup.whatsapp')}
                      type="tel"
                      placeholder={t('auth.signup.whatsapp_ph')}
                      required
                      value={formData.whatsapp}
                      onChange={(e) => setFormData({ ...formData, whatsapp: e.target.value })}
                    />
                  </div>

                  <Input
                    label={t('auth.signup.org')}
                    placeholder={t('auth.signup.org_ph')}
                    required
                    value={formData.organization}
                    onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                  />
                </>
              )}

              {mode === 'login' && (
                <>
                  <Input
                    label={t('auth.login.email')}
                    type="email"
                    placeholder={t('auth.login.email_ph')}
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  />
                </>
              )}

              <div className="relative">
                <Input
                  label={mode === 'login' ? t('auth.login.password') : t('auth.signup.password')}
                  type={showPassword ? 'text' : 'password'}
                  placeholder={mode === 'login' ? t('auth.login.password_ph') : t('auth.signup.password_ph')}
                  required
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="text-text-muted hover:text-text-dim"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  }
                />
              </div>

              <Button
                type="submit"
                className="w-full"
                size="lg"
                isLoading={isLoading}
              >
                {mode === 'login' 
                  ? (isLoading ? t('auth.login.btn_loading') : t('auth.login.btn'))
                  : (isLoading ? t('auth.signup.btn_loading') : t('auth.signup.btn'))
                }
              </Button>
            </form>

            <p className="text-center mt-6 text-text-muted text-sm">
              {mode === 'login' ? t('auth.login.switch') : ''}{' '}
              <button
                type="button"
                onClick={() => {
                  setMode(mode === 'login' ? 'signup' : 'login')
                  setError('')
                }}
                className="text-primary font-bold hover:underline underline-offset-2"
              >
                {mode === 'login' ? t('auth.login.switch_link') : t('auth.signup.switch_link')}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
