import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { getOrganizations, deleteOrganization } from '@/api/admin'
import { Button, Modal } from '@/components/ui'

interface Organization {
  id: string
  name: string
  created_at: string
  user_count?: number
}

export default function AdminOrganizations() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [deletingOrg, setDeletingOrg] = useState<Organization | null>(null)

  const { data: organizations = [] } = useQuery({
    queryKey: ['organizations'],
    queryFn: getOrganizations,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteOrganization,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
      setDeletingOrg(null)
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-text tracking-tight">{t('admin.organizations.title')}</h1>
          <p className="text-sm text-text-muted mt-1">{t('admin.organizations.subtitle')}</p>
        </div>
        <Button>
          <Plus className="w-4 h-4" />
          {t('admin.organizations.add')}
        </Button>
      </div>

      <div className="bg-card-bg border border-border rounded-2xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-table-header">
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.organizations.col.name')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.organizations.col.users')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.organizations.col.created')}</th>
              <th className="text-right py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.organizations.col.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {organizations.map((org: Organization) => (
              <tr key={org.id} className="border-b border-border/50 hover:bg-table-row-hover transition-colors">
                <td className="py-4 px-5 font-semibold text-text">{org.name}</td>
                <td className="py-4 px-5 text-text-dim">{org.user_count ?? 0}</td>
                <td className="py-4 px-5 text-text-muted text-sm">{formatDate(org.created_at)}</td>
                <td className="py-4 px-5">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => setDeletingOrg(org)}
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
        isOpen={!!deletingOrg}
        onClose={() => setDeletingOrg(null)}
        title={t('common.delete')}
      >
        <p className="text-text-dim mb-4">
          ¿Eliminar organización <strong>{deletingOrg?.name}</strong>?
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => setDeletingOrg(null)} className="flex-1">
            {t('common.cancel')}
          </Button>
          <Button
            variant="danger"
            onClick={() => deletingOrg && deleteMutation.mutate(deletingOrg.id)}
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
