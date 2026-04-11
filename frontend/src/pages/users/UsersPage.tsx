import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Plus, Trash2, UserCheck, UserX } from 'lucide-react'
import { getUsers, deleteUser, reactivateUser } from '@/api/users'
import { getRoles } from '@/api/roles'
import { Button, Input, Select, Modal, Badge, Alert } from '@/components/ui'
import type { User, Role } from '@/types'

export default function UsersPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [deletingUser, setDeletingUser] = useState<User | null>(null)
  const [showAddUser, setShowAddUser] = useState(false)

  const { data: users = [] } = useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setDeletingUser(null)
    },
  })

  const reactivateMutation = useMutation({
    mutationFn: reactivateUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })

  const filteredUsers = users.filter(user =>
    user.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    user.email?.toLowerCase().includes(search.toLowerCase()) ||
    user.whatsapp_number?.includes(search)
  )

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-text tracking-tight">{t('users.title')}</h1>
          <p className="text-sm text-text-muted mt-1">{t('users.subtitle')}</p>
        </div>
        <Button onClick={() => setShowAddUser(true)}>
          <Plus className="w-4 h-4" />
          {t('users.add_user')}
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <Input
          placeholder={t('users.search')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          leftIcon={<Search className="w-4 h-4" />}
          className="max-w-sm"
        />
      </div>

      <div className="bg-card-bg border border-border rounded-2xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-table-header">
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('users.col.name')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('users.col.email')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('users.col.whatsapp')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('users.col.role')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('users.col.status')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('users.col.joined')}</th>
              <th className="text-right py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('users.col.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => (
              <tr key={user.id} className="border-b border-border/50 hover:bg-table-row-hover transition-colors">
                <td className="py-4 px-5 font-semibold text-text">{user.full_name || user.username}</td>
                <td className="py-4 px-5 text-text-dim">{user.email}</td>
                <td className="py-4 px-5 text-text-dim font-mono text-sm">{user.whatsapp_number}</td>
                <td className="py-4 px-5 text-text-dim">{user.role?.name || '—'}</td>
                <td className="py-4 px-5">
                  <Badge variant={user.is_active ? 'active' : 'inactive'}>
                    {user.is_active ? t('common.active') : t('common.inactive')}
                  </Badge>
                </td>
                <td className="py-4 px-5 text-text-muted text-sm">{formatDate(user.created_at)}</td>
                <td className="py-4 px-5">
                  <div className="flex items-center justify-end gap-2">
                    {user.is_active ? (
                      <button
                        onClick={() => reactivateMutation.mutate(user.id)}
                        className="p-2 text-text-muted hover:text-text-dim hover:bg-surface rounded-lg transition-colors"
                        title="Desactivar"
                      >
                        <UserX className="w-4 h-4" />
                      </button>
                    ) : (
                      <button
                        onClick={() => reactivateMutation.mutate(user.id)}
                        className="p-2 text-badge-active-color hover:bg-badge-active-bg rounded-lg transition-colors"
                        title="Reactivar"
                      >
                        <UserCheck className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => setDeletingUser(user)}
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

        {filteredUsers.length === 0 && (
          <div className="text-center py-12 text-text-muted">
            <span className="text-4xl">👥</span>
            <p className="mt-2 text-sm">{t('users.empty')}</p>
          </div>
        )}
      </div>

      <Modal
        isOpen={!!deletingUser}
        onClose={() => setDeletingUser(null)}
        title={t('users.modal.delete_title')}
      >
        <p className="text-text-dim mb-4">{t('users.modal.delete_confirm')}</p>
        <p className="text-text-muted text-sm mb-6">{t('users.modal.delete_warning')}</p>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => setDeletingUser(null)} className="flex-1">
            {t('common.cancel')}
          </Button>
          <Button
            variant="danger"
            onClick={() => deletingUser && deleteMutation.mutate(deletingUser.id)}
            isLoading={deleteMutation.isPending}
            className="flex-1"
          >
            {t('common.delete')}
          </Button>
        </div>
      </Modal>

      <AddUserModal
        isOpen={showAddUser}
        onClose={() => setShowAddUser(false)}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ['users'] })}
      />
    </div>
  )
}

function AddUserModal({ isOpen, onClose, onSuccess }: { isOpen: boolean; onClose: () => void; onSuccess: () => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    full_name: '',
    job_title: '',
    whatsapp_number: '',
    role_id: '',
  })
  const [error, setError] = useState('')

  const { data: roles = [] } = useQuery({
    queryKey: ['roles'],
    queryFn: getRoles,
  })

  const mutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const { createUser } = await import('@/api/users')
      return createUser({
        full_name: data.full_name,
        job_title: data.job_title || undefined,
        whatsapp_number: data.whatsapp_number,
        role_id: data.role_id,
        username: data.full_name.toLowerCase().replace(/\s+/g, '.'),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      onSuccess()
      onClose()
      setFormData({ full_name: '', job_title: '', whatsapp_number: '', role_id: '' })
    },
    onError: (err: Error) => setError(err.message),
  })

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('dashboard.modal.add_title')}>
      <form onSubmit={(e) => { e.preventDefault(); mutation.mutate(formData) }}>
        <div className="space-y-4">
          <Input
            label={t('dashboard.modal.fullname')}
            required
            value={formData.full_name}
            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
          />
          <Input
            label={t('dashboard.modal.jobtitle')}
            value={formData.job_title}
            onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
          />
          <Input
            label={t('dashboard.modal.whatsapp')}
            required
            value={formData.whatsapp_number}
            onChange={(e) => setFormData({ ...formData, whatsapp_number: e.target.value })}
          />
          <Select
            label={t('dashboard.modal.role')}
            required
            value={formData.role_id}
            onChange={(e) => setFormData({ ...formData, role_id: e.target.value })}
            options={roles.map((r: Role) => ({ value: r.id, label: r.name }))}
            placeholder={t('dashboard.modal.role_ph')}
          />
          {error && <Alert variant="error">{error}</Alert>}
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={onClose} className="flex-1">
              {t('common.cancel')}
            </Button>
            <Button type="submit" isLoading={mutation.isPending} className="flex-1">
              {t('dashboard.modal.btn')}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  )
}
