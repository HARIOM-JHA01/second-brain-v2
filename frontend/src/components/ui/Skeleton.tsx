import { clsx } from 'clsx'

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string | number
  height?: string | number
}

export function Skeleton({ 
  className, 
  variant = 'text', 
  width, 
  height 
}: SkeletonProps) {
  const variants = {
    text: 'h-4 rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg',
  }

  return (
    <div
      className={clsx(
        'animate-shimmer',
        variants[variant],
        className
      )}
      style={{
        width: width,
        height: height,
      }}
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="border border-border rounded-2xl p-5" style={{ backgroundColor: 'var(--card-bg)' }}>
      <div className="flex flex-col gap-3">
        <Skeleton width="60%" height={16} />
        <Skeleton width="40%" height={12} />
        <Skeleton height={100} className="mt-2" />
      </div>
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="border border-border rounded-2xl overflow-hidden" style={{ backgroundColor: 'var(--card-bg)' }}>
      <div className="p-4 border-b border-border">
        <Skeleton width="30%" height={16} />
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 p-4">
            <Skeleton width="20%" height={14} />
            <Skeleton width="15%" height={14} />
            <Skeleton width="25%" height={14} />
            <Skeleton width="10%" height={14} />
          </div>
        ))}
      </div>
    </div>
  )
}
