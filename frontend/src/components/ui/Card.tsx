import { ReactNode } from 'react'
import { clsx } from 'clsx'

interface CardProps {
  children: ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

export function Card({ children, className, padding = 'md' }: CardProps) {
  const paddings = {
    none: '',
    sm: 'p-3',
    md: 'p-5',
    lg: 'p-6',
  }

  return (
    <div
      className={clsx(
        'border border-border rounded-2xl transition-all duration-300',
        paddings[padding],
        className
      )}
      style={{ backgroundColor: 'var(--card-bg)' }}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps {
  children: ReactNode
  className?: string
  action?: ReactNode
}

export function CardHeader({ children, className, action }: CardHeaderProps) {
  return (
    <div className={clsx('flex items-center justify-between mb-4', className)}>
      <div>{children}</div>
      {action && <div>{action}</div>}
    </div>
  )
}

interface CardTitleProps {
  children: ReactNode
  subtitle?: string
}

export function CardTitle({ children, subtitle }: CardTitleProps) {
  return (
    <div>
      <h3 className="text-sm font-bold" style={{ color: 'var(--text)' }}>{children}</h3>
      {subtitle && (
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{subtitle}</p>
      )}
    </div>
  )
}
