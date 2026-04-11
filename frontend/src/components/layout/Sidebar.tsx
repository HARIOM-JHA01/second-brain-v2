import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { 
  LayoutDashboard, 
  Users, 
  FileText, 
  Target, 
  Settings,
  Shield
} from 'lucide-react'
import { clsx } from 'clsx'

interface NavItem {
  to: string
  icon: React.ReactNode
  labelKey: string
  section?: string
}

const navItems: NavItem[] = [
  { to: '/app/dashboard', icon: <LayoutDashboard className="w-[18px] h-[18px]" />, labelKey: 'sidebar.dashboard', section: 'sidebar.main' },
  { to: '/app/users', icon: <Users className="w-[18px] h-[18px]" />, labelKey: 'sidebar.users', section: 'sidebar.manage' },
  { to: '/app/documents', icon: <FileText className="w-[18px] h-[18px]" />, labelKey: 'sidebar.documents', section: 'sidebar.manage' },
  { to: '/app/scenarios', icon: <Target className="w-[18px] h-[18px]" />, labelKey: 'sidebar.scenarios', section: 'sidebar.manage' },
  { to: '/app/settings', icon: <Settings className="w-[18px] h-[18px]" />, labelKey: 'sidebar.settings', section: 'sidebar.config' },
]

const adminItems: NavItem[] = [
  { to: '/app/admin', icon: <Shield className="w-[18px] h-[18px]" />, labelKey: 'admin.dashboard.title', section: 'sidebar.admin' },
]

export function Sidebar() {
  const { t } = useTranslation()

  const renderSection = (sectionKey: string, items: NavItem[]) => (
        <div key={sectionKey} className="mt-1">
      <div className="px-5 py-3 text-[10px] font-bold uppercase tracking-widest text-text-muted">
        {t(sectionKey)}
      </div>
      <div className="space-y-0.5">
        {items.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/app/admin'}
            className={({ isActive }) => 
              clsx(
                'flex items-center gap-3 px-5 py-2.5 mx-2 rounded-lg text-sm font-medium transition-all duration-200 border border-transparent',
                isActive 
                  ? 'bg-sidebar-active border-red-500/20 text-text font-semibold' 
                  : 'text-text-dim hover:bg-surface-hover hover:text-text'
              )
            }
          >
            <span>{item.icon}</span>
            <span>{t(item.labelKey)}</span>
          </NavLink>
        ))}
      </div>
    </div>
  )

  return (
    <aside className="w-[228px] flex-shrink-0 bg-sidebar-bg border-r border-border py-5 flex flex-col transition-colors duration-300">
      {renderSection('sidebar.main', navItems.filter(i => !i.section || i.section === 'sidebar.main'))}
      {renderSection('sidebar.manage', navItems.filter(i => i.section === 'sidebar.manage'))}
      {renderSection('sidebar.admin', adminItems)}
      {navItems.find(i => i.section === 'sidebar.config') && 
        renderSection('sidebar.config', navItems.filter(i => i.section === 'sidebar.config'))}
    </aside>
  )
}
