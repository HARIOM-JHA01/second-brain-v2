import { clsx } from 'clsx'

interface BadgeProps {
  variant?: 'active' | 'inactive' | 'primary' | 'secondary'
  children: React.ReactNode
  className?: string
}

export function Badge({ variant = 'active', children, className }: BadgeProps) {
  const variants = {
    active: 'bg-badge-active-bg text-badge-active-color',
    inactive: 'bg-badge-inactive-bg text-badge-inactive-color',
    primary: 'bg-primary/10 text-primary',
    secondary: 'bg-secondary/10 text-secondary',
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold',
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  )
}
