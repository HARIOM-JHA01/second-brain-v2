import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Key, ToggleLeft, ToggleRight, Trash2 } from 'lucide-react'
import { getAdminUsers, setUserPassword, toggleUserActive, deleteAdminUser } from '@/api/admin'
import { Button, Modal, Input, Badge } from '@/components/ui'

interface AdminUser {
  id: string
  email: string
  full_name: string
  is_active: boolean
  organization_name: string
  created_at: string
}

export default function AdminUsers() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [password, setPassword] = useState('')

  const { data: users = [] } = useQuery({
    queryKey: ['adminUsers'],
    queryFn: getAdminUsers,
  })

  const passwordMutation = useMutation({
    mutationFn: ({ userId, password }: { userId: string; password: string }) =>
      setUserPassword(userId, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] })
      setShowPasswordModal(false)
      setSelectedUser(null)
      setPassword('')
    },
  })

  const toggleMutation = useMutation({
    mutationFn: ({ profileId, isActive }: { profileId: string; isActive: boolean }) =>
      toggleUserActive(profileId, isActive),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['adminUsers'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAdminUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] })
      setShowDeleteModal(false)
      setSelectedUser(null)
    },
  })

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-text tracking-tight">{t('admin.users.title')}</h1>
        <p className="text-sm text-text-muted mt-1">{t('admin.users.subtitle')}</p>
      </div>

      <div className="bg-card-bg border border-border rounded-2xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-table-header">
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.users.col.name')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.users.col.email')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.users.col.organization')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.users.col.status')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.users.col.joined')}</th>
              <th className="text-right py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.users.col.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user: AdminUser) => (
              <tr key={user.id} className="border-b border-border/50 hover:bg-table-row-hover transition-colors">
                <td className="py-4 px-5 font-semibold text-text">{user.full_name || '—'}</td>
                <td className="py-4 px-5 text-text-dim">{user.email}</td>
                <td className="py-4 px-5 text-text-dim">{user.organization_name}</td>
                <td className="py-4 px-5">
                  <Badge variant={user.is_active ? 'active' : 'inactive'}>
                    {user.is_active ? t('common.active') : t('common.inactive')}
                  </Badge>
                </td>
                <td className="py-4 px-5 text-text-muted text-sm">{formatDate(user.created_at)}</td>
                <td className="py-4 px-5">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => { setSelectedUser(user); setShowPasswordModal(true) }}
                      className="p-2 text-text-muted hover:text-text-dim hover:bg-surface rounded-lg transition-colors"
                      title={t('admin.users.set_password')}
                    >
                      <Key className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => toggleMutation.mutate({ profileId: user.id, isActive: !user.is_active })}
                      className={`p-2 rounded-lg transition-colors ${
                        user.is_active 
                          ? 'text-text-muted hover:text-error hover:bg-badge-inactive-bg' 
                          : 'text-badge-active-color hover:bg-badge-active-bg'
                      }`}
                      title={t('admin.users.toggle_active')}
                    >
                      {user.is_active ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => { setSelectedUser(user); setShowDeleteModal(true) }}
                      className="p-2 text-text-muted hover:text-error hover:bg-badge-inactive-bg rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal
        isOpen={showPasswordModal}
        onClose={() => { setShowPasswordModal(false); setSelectedUser(null); setPassword('') }}
        title={t('admin.users.set_password')}
      >
        <form onSubmit={(e) => { e.preventDefault(); selectedUser && passwordMutation.mutate({ userId: selectedUser.id, password }) }}>
          <p className="text-text-dim mb-4">
            {t('common.required')}: <strong>{selectedUser?.email}</strong>
          </p>
          <Input
            label="Nueva contraseña"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <div className="flex gap-3 mt-6">
            <Button type="button" variant="secondary" onClick={() => { setShowPasswordModal(false); setSelectedUser(null) }} className="flex-1">
              {t('common.cancel')}
            </Button>
            <Button type="submit" isLoading={passwordMutation.isPending} className="flex-1">
              {t('common.save')}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={showDeleteModal}
        onClose={() => { setShowDeleteModal(false); setSelectedUser(null) }}
        title={t('common.delete')}
      >
        <p className="text-text-dim mb-4">
          ¿Eliminar usuario <strong>{selectedUser?.full_name || selectedUser?.email}</strong>?
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => { setShowDeleteModal(false); setSelectedUser(null) }} className="flex-1">
            {t('common.cancel')}
          </Button>
          <Button
            variant="danger"
            onClick={() => selectedUser && deleteMutation.mutate(selectedUser.id)}
            isLoading={deleteMutation.isPending}
            className="flex-1"
          >
            {t('common.delete')}
          </Button>
        </div>
      </Modal>
    </div>
  )
}
