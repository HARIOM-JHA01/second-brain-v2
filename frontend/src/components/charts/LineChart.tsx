import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardTitle } from '../ui/Card'

interface LineChartProps {
  title: string
  subtitle?: string
  data: { label: string; value: number }[]
  color?: string
  loading?: boolean
}

export function LineChart({ title, subtitle, data, color = '#dc2626', loading }: LineChartProps) {
  const isDark = document.documentElement.getAttribute('data-theme') !== 'light'
  
  const chartData = data.map(item => ({
    name: item.label,
    value: item.value,
  }))

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

      <div className="h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <RechartsLineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
            <CartesianGrid 
              strokeDasharray="3 3" 
              stroke={isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'} 
            />
            <XAxis 
              dataKey="name" 
              tick={{ fill: isDark ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.4)', fontSize: 11 }}
              axisLine={{ stroke: 'transparent' }}
              tickLine={{ stroke: 'transparent' }}
            />
            <YAxis 
              tick={{ fill: isDark ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.4)', fontSize: 11 }}
              axisLine={{ stroke: 'transparent' }}
              tickLine={{ stroke: 'transparent' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: isDark ? '#1e2130' : '#fff',
                border: '1px solid rgba(220,38,38,0.3)',
                borderRadius: 8,
                color: isDark ? '#e2e8f0' : '#1e293b',
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={{ r: 3, fill: color }}
              activeDot={{ r: 6, fill: color }}
              fill={`${color}20`}
            />
          </RechartsLineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}
