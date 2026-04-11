import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { LineChart } from '@/components/charts/LineChart'
import { BarChart } from '@/components/charts/BarChart'
import { DonutChart } from '@/components/charts/DonutChart'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { AddUserModal } from './AddUserModal'
import { getDashboardStats, getUsers } from '@/api/users'

export default function DashboardPage() {
  const { t } = useTranslation()
  const [period, setPeriod] = useState<7 | 30>(30)
  const [showAddUser, setShowAddUser] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboardStats', refreshKey],
    queryFn: getDashboardStats,
  })

  const { data: users = [] } = useQuery({
    queryKey: ['users', refreshKey],
    queryFn: getUsers,
  })

  const messageChartData = useMemo(() => {
    if (!stats?.messages_chart) return []
    const days = period === 7 ? 7 : 30
    const map: Record<string, number> = {}
    stats.messages_chart.forEach((r) => { map[r.day] = r.count })
    const result = []
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date()
      d.setDate(d.getDate() - i)
      const key = d.toISOString().slice(0, 10)
      result.push({
        label: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        value: map[key] ?? 0,
      })
    }
    return result
  }, [stats, period])

  const signupsChartData = useMemo(() => {
    if (!stats?.signups_chart) return []
    const days = period === 7 ? 7 : 30
    const map: Record<string, number> = {}
    stats.signups_chart.forEach((r) => { map[r.day] = r.count })
    const result = []
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date()
      d.setDate(d.getDate() - i)
      const key = d.toISOString().slice(0, 10)
      result.push({
        label: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        value: map[key] ?? 0,
      })
    }
    return result
  }, [stats, period])

  const teamStatusData = useMemo(() => [
    { label: 'lbl.active', value: stats?.active_users ?? 0, color: '#34d399' },
    { label: 'lbl.inactive', value: stats?.inactive_users ?? 0, color: '#f87171' },
  ], [stats])

  const messageTypesData = useMemo(() => {
    const breakdown = stats?.message_types_breakdown ?? { text: 0, audio: 0, image: 0, document: 0 }
    return [
      { label: 'lbl.text', value: breakdown.text, color: '#60a5fa' },
      { label: 'lbl.audio', value: breakdown.audio, color: '#ef4444' },
      { label: 'lbl.images', value: breakdown.image, color: '#34d399' },
      { label: 'lbl.docs', value: breakdown.document, color: '#fb923c' },
    ]
  }, [stats])

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-text tracking-tight">
            {stats?.org_name ? `${stats.org_name} ${t('dashboard.title')}` : t('dashboard.title')}
          </h1>
          <p className="text-sm text-text-muted mt-1">
            {new Date().toLocaleDateString('es-ES', { weekday: 'long', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-surface border border-border rounded-lg p-0.5">
            <button
              onClick={() => setPeriod(7)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                period === 7 ? 'bg-primary text-white' : 'text-text-muted hover:text-text'
              }`}
            >
              7d
            </button>
            <button
              onClick={() => setPeriod(30)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                period === 30 ? 'bg-primary text-white' : 'text-text-muted hover:text-text'
              }`}
            >
              30d
            </button>
          </div>
          <Button onClick={() => setShowAddUser(true)}>
            {t('dashboard.add_user')}
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <StatPill label={t('dashboard.pill.users')} value={stats?.total_users ?? '—'} color="#60a5fa" />
        <StatPill label={t('dashboard.pill.active')} value={stats?.active_users ?? '—'} color="#34d399" />
        <StatPill label={t('dashboard.pill.messages')} value={period === 7 ? stats?.messages_7d ?? '—' : stats?.messages_30d ?? '—'} color="#ef4444" />
        <StatPill label={t('dashboard.pill.docs')} value={stats?.total_docs ?? '—'} color="#fb923c" />
        <StatPill label={t('dashboard.pill.avg_resp')} value={stats?.avg_response_ms != null ? `${stats.avg_response_ms} ms` : '—'} color="#f472b6" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <LineChart
            title={t('dashboard.chart.msg_activity')}
            subtitle={t('dashboard.chart.msg_per_day')}
            data={messageChartData}
            loading={statsLoading}
          />
        </div>
        <div>
          <DonutChart
            title={t('dashboard.chart.team_status')}
            subtitle={t('dashboard.chart.active_vs')}
            data={teamStatusData}
            centerValue={`${Math.round((stats?.active_users ?? 0) / ((stats?.active_users ?? 0) + (stats?.inactive_users ?? 1)) * 100)}%`}
            centerLabel={t('dashboard.lbl.active')}
            loading={statsLoading}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <BarChart
          title={t('dashboard.chart.team_growth')}
          subtitle={`+${period === 7 ? stats?.new_users_7d ?? 0 : stats?.new_users_30d ?? 0} ${t('dashboard.lbl.new_week')}`}
          data={signupsChartData}
          loading={statsLoading}
        />
        <DonutChart
          title={t('dashboard.chart.msg_breakdown')}
          subtitle={t('dashboard.chart.by_type')}
          data={messageTypesData}
          loading={statsLoading}
        />
      </div>

      <div className="bg-card-bg border border-border rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold text-text">{t('dashboard.team_members')}</h2>
          <a href="/app/users" className="text-xs text-primary font-semibold hover:opacity-80">
            {t('dashboard.view_all')}
          </a>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('dashboard.col.name')}</th>
                <th className="text-left py-3 px-4 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('dashboard.col.whatsapp')}</th>
                <th className="text-left py-3 px-4 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('dashboard.col.jobtitle')}</th>
                <th className="text-left py-3 px-4 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('dashboard.col.role')}</th>
                <th className="text-left py-3 px-4 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('dashboard.col.status')}</th>
                <th className="text-left py-3 px-4 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('dashboard.col.joined')}</th>
              </tr>
            </thead>
            <tbody>
              {users.slice(0, 8).map((user) => (
                <tr key={user.id} className="border-b border-border/50 hover:bg-surface-hover transition-colors">
                  <td className="py-3 px-4 font-semibold text-text">{user.full_name || user.username || '—'}</td>
                  <td className="py-3 px-4 text-text-dim font-mono text-sm">{user.whatsapp_number || '—'}</td>
                  <td className="py-3 px-4 text-text-muted">{user.job_title || '—'}</td>
                  <td className="py-3 px-4 text-text-dim">{user.role?.name || '—'}</td>
                  <td className="py-3 px-4">
                    <Badge variant={user.is_active ? 'active' : 'inactive'}>
                      {user.is_active ? t('common.active') : t('common.inactive')}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-text-muted text-sm">{user.created_at ? formatDate(user.created_at) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && (
            <div className="text-center py-8 text-text-muted">
              <span className="text-2xl">👥</span>
              <p className="mt-2 text-sm">{t('dashboard.empty')}</p>
            </div>
          )}
        </div>
      </div>

      <AddUserModal
        isOpen={showAddUser}
        onClose={() => setShowAddUser(false)}
        onSuccess={() => setRefreshKey(k => k + 1)}
      />
    </div>
  )
}

function StatPill({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="flex items-center gap-2 bg-card-bg border border-border rounded-full px-4 py-2 hover:border-border-hover transition-colors">
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-xs font-semibold text-text-dim">{label}</span>
      <span className="text-sm font-extrabold text-text">{value}</span>
    </div>
  )
}
