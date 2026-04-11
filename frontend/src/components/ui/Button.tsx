import { ButtonHTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'
import { Loader2 } from 'lucide-react'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'success'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    className, 
    variant = 'primary', 
    size = 'md', 
    isLoading = false, 
    leftIcon, 
    rightIcon, 
    children, 
    disabled,
    ...props 
  }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center gap-2 font-semibold rounded-lg cursor-pointer border-none transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed'
    
    const variants = {
      primary: 'bg-gradient-to-br from-primary to-secondary text-white shadow-lg hover:shadow-xl hover:-translate-y-0.5',
      secondary: 'bg-surface border border-border text-text-dim hover:bg-surface-hover hover:text-text',
      danger: 'bg-badge-inactive-bg border border-red-200/20 text-badge-inactive-color hover:bg-red-200/20',
      success: 'bg-badge-active-bg border border-green-200/20 text-badge-active-color hover:bg-green-200/20',
    }
    
    const sizes = {
      sm: 'px-3 py-1.5 text-xs rounded-md',
      md: 'px-4 py-2.5 text-sm',
      lg: 'px-6 py-3 text-base',
    }

    return (
      <button
        ref={ref}
        className={clsx(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : leftIcon}
        {children}
        {!isLoading && rightIcon}
      </button>
    )
  }
)

Button.displayName = 'Button'
