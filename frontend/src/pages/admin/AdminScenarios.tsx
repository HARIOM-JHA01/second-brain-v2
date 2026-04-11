import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Edit2 } from 'lucide-react'
import { getScenarios, deleteScenario, createScenario } from '@/api/admin'
import { Button, Modal, Input, Alert } from '@/components/ui'

interface Scenario {
  id: string
  name: string
  description: string
  created_at: string
}

export default function AdminScenarios() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [deletingScenario, setDeletingScenario] = useState<Scenario | null>(null)
  const [formData, setFormData] = useState({ name: '', description: '' })
  const [error, setError] = useState('')

  const { data: scenarios = [] } = useQuery({
    queryKey: ['adminScenarios'],
    queryFn: getScenarios,
  })

  const createMutation = useMutation({
    mutationFn: createScenario,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminScenarios'] })
      setShowCreateModal(false)
      setFormData({ name: '', description: '' })
    },
    onError: (err: Error) => setError(err.message),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteScenario,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminScenarios'] })
      setDeletingScenario(null)
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
          <h1 className="text-2xl font-extrabold text-text tracking-tight">{t('admin.scenarios.title')}</h1>
          <p className="text-sm text-text-muted mt-1">{t('admin.scenarios.subtitle')}</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4" />
          {t('admin.scenarios.add')}
        </Button>
      </div>

      <div className="bg-card-bg border border-border rounded-2xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-table-header">
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.scenarios.col.name')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.scenarios.col.description')}</th>
              <th className="text-left py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.scenarios.col.created')}</th>
              <th className="text-right py-4 px-5 text-[11px] font-bold uppercase tracking-wider text-text-muted">{t('admin.scenarios.col.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((scenario: Scenario) => (
              <tr key={scenario.id} className="border-b border-border/50 hover:bg-table-row-hover transition-colors">
                <td className="py-4 px-5 font-semibold text-text">{scenario.name}</td>
                <td className="py-4 px-5 text-text-dim">{scenario.description || '—'}</td>
                <td className="py-4 px-5 text-text-muted text-sm">{formatDate(scenario.created_at)}</td>
                <td className="py-4 px-5">
                  <div className="flex items-center justify-end gap-1">
                    <button className="p-2 text-text-muted hover:text-text-dim hover:bg-surface rounded-lg transition-colors">
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setDeletingScenario(scenario)}
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
        isOpen={showCreateModal}
        onClose={() => { setShowCreateModal(false); setFormData({ name: '', description: '' }); setError('') }}
        title={t('admin.scenarios.add')}
      >
        <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(formData) }}>
          <div className="space-y-4">
            <Input
              label="Nombre"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
            <Input
              label="Descripción"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
            {error && <Alert variant="error">{error}</Alert>}
            <div className="flex gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={() => setShowCreateModal(false)} className="flex-1">
                {t('common.cancel')}
              </Button>
              <Button type="submit" isLoading={createMutation.isPending} className="flex-1">
                {t('common.save')}
              </Button>
            </div>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={!!deletingScenario}
        onClose={() => setDeletingScenario(null)}
        title={t('common.delete')}
      >
        <p className="text-text-dim mb-4">
          ¿Eliminar escenario <strong>{deletingScenario?.name}</strong>?
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => setDeletingScenario(null)} className="flex-1">
            {t('common.cancel')}
          </Button>
          <Button
            variant="danger"
            onClick={() => deletingScenario && deleteMutation.mutate(deletingScenario.id)}
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
