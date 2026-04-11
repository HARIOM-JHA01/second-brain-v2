import { SelectHTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  options: Array<{ value: string; label: string }>
  placeholder?: string
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, options, placeholder, ...props }, ref) => {
    return (
      <div className="mb-4">
        {label && (
          <label className="block text-sm font-semibold text-text-dim mb-2">
            {label}
            {props.required && <span className="text-primary ml-1">*</span>}
          </label>
        )}
        <select
          ref={ref}
          className={clsx(
            'w-full px-4 py-3 bg-input-bg border border-border rounded-lg text-sm font-normal outline-none transition-all duration-200 cursor-pointer appearance-none pr-10',
            error && 'border-error',
            className
          )}
          style={{ 
            color: 'var(--input-color)',
            backgroundColor: 'var(--input-bg)',
            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='5'%3E%3Cpath d='M0 0l4 5 4-5z' fill='rgba(160,160,180,0.6)'/%3E%3C/svg%3E")`,
            backgroundRepeat: 'no-repeat',
            backgroundPosition: 'right 12px center',
            backgroundSize: '8px 5px'
          }}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {error && (
          <p className="mt-1 text-xs text-error">{error}</p>
        )}
      </div>
    )
  }
)

Select.displayName = 'Select'
