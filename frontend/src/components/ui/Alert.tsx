import { clsx } from 'clsx'
import { AlertCircle, CheckCircle, Info, XCircle } from 'lucide-react'

interface AlertProps {
  variant?: 'success' | 'error' | 'info' | 'warning'
  children: React.ReactNode
  className?: string
  onClose?: () => void
}

export function Alert({ variant = 'info', children, className, onClose }: AlertProps) {
  const variants = {
    success: 'bg-badge-active-bg text-badge-active-color border border-green-200/20',
    error: 'bg-badge-inactive-bg text-error border border-red-200/20',
    info: 'bg-primary/10 text-primary border border-primary/20',
    warning: 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20',
  }

  const icons = {
    success: CheckCircle,
    error: XCircle,
    info: Info,
    warning: AlertCircle,
  }

  const Icon = icons[variant]

  return (
    <div
      className={clsx(
        'flex items-start gap-3 px-4 py-3 rounded-lg text-sm',
        variants[variant],
        className
      )}
    >
      <Icon className="h-5 w-5 flex-shrink-0 mt-0.5" />
      <div className="flex-1">{children}</div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-current opacity-60 hover:opacity-100"
        >
          ×
        </button>
      )}
    </div>
  )
}
