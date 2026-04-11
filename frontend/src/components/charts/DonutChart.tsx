import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { useTranslation } from 'react-i18next'
import { Card, CardTitle } from '../ui/Card'

interface DonutChartProps {
  title: string
  subtitle?: string
  data: { label: string; value: number; color: string }[]
  centerLabel?: string
  centerValue?: string | number
  loading?: boolean
}

export function DonutChart({ 
  title, 
  subtitle, 
  data, 
  centerLabel, 
  centerValue, 
  loading 
}: DonutChartProps) {
  const { t } = useTranslation()
  const isDark = document.documentElement.getAttribute('data-theme') !== 'light'

  return (
    <Card className="relative">
      {loading && (
        <div className="absolute inset-0 rounded-2xl z-10 flex items-center justify-center" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}
      
      <div className="flex items-start justify-between mb-4">
        <CardTitle subtitle={subtitle}>{title}</CardTitle>
      </div>

      <div className="h-[170px] relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={75}
              paddingAngle={2}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: isDark ? '#1e2130' : '#fff',
                border: '1px solid rgba(220,38,38,0.3)',
                borderRadius: 8,
                color: isDark ? '#e2e8f0' : '#1e293b',
              }}
              formatter={(value: number) => [value, '']}
            />
          </PieChart>
        </ResponsiveContainer>
        
        {(centerValue !== undefined || centerLabel) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            {centerValue !== undefined && (
              <span className="text-2xl font-black tracking-tighter" style={{ color: 'var(--text)' }}>
                {centerValue}
              </span>
            )}
            {centerLabel && (
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {centerLabel}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="flex justify-center gap-4 mt-4 text-xs" style={{ color: 'var(--text-muted)' }}>
        {data.map((item, index) => (
          <span key={index}>
            <span style={{ color: item.color }} className="font-bold">{item.value}</span>{' '}
            {t(item.label)}
          </span>
        ))}
      </div>
    </Card>
  )
}
