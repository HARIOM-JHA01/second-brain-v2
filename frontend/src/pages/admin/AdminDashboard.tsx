import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Building2, Users, UserCheck, Target } from 'lucide-react'
import { getAdminStats } from '@/api/admin'
import { Card } from '@/components/ui'

export default function AdminDashboard() {
  const { t } = useTranslation()

  const { data: stats, isLoading } = useQuery({
    queryKey: ['adminStats'],
    queryFn: getAdminStats,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-text tracking-tight">{t('admin.dashboard.title')}</h1>
        <p className="text-sm text-text-muted mt-1">{t('admin.dashboard.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Building2 className="w-5 h-5" />}
          label={t('admin.dashboard.stats.organizations')}
          value={stats?.total_organizations ?? '—'}
          color="#60a5fa"
          loading={isLoading}
        />
        <StatCard
          icon={<Users className="w-5 h-5" />}
          label={t('admin.dashboard.stats.users')}
          value={stats?.total_users ?? '—'}
          color="#34d399"
          loading={isLoading}
        />
        <StatCard
          icon={<UserCheck className="w-5 h-5" />}
          label={t('admin.dashboard.stats.active_users')}
          value={stats?.active_users ?? '—'}
          color="#4ade80"
          loading={isLoading}
        />
        <StatCard
          icon={<Target className="w-5 h-5" />}
          label={t('admin.dashboard.stats.scenarios')}
          value={stats?.scenarios_count ?? '—'}
          color="#f472b6"
          loading={isLoading}
        />
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, color, loading }: { icon: React.ReactNode; label: string; value: string | number; color: string; loading?: boolean }) {
  return (
    <Card className="relative">
      {loading && (
        <div className="absolute inset-0 bg-card-bg/80 rounded-2xl z-10 flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-text-muted">{label}</p>
          <p className="text-3xl font-black text-text mt-1 tracking-tighter">{value}</p>
        </div>
        <div 
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ backgroundColor: `${color}20`, color }}
        >
          {icon}
        </div>
      </div>
    </Card>
  )
}
