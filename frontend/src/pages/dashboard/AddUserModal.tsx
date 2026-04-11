import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Modal, Button, Input, Select, Alert } from '@/components/ui'
import { getRoles } from '@/api/roles'
import { createUser } from '@/api/users'
import type { Role } from '@/types'
import { useQuery } from '@tanstack/react-query'

interface AddUserModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function AddUserModal({ isOpen, onClose, onSuccess }: AddUserModalProps) {
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState({
    full_name: '',
    job_title: '',
    whatsapp_number: '',
    role_id: '',
  })

  const { data: roles = [] } = useQuery({
    queryKey: ['roles'],
    queryFn: getRoles,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await createUser({
        full_name: formData.full_name,
        job_title: formData.job_title || undefined,
        whatsapp_number: formData.whatsapp_number,
        role_id: formData.role_id,
        username: formData.full_name.toLowerCase().replace(/\s+/g, '.'),
      })
      setFormData({ full_name: '', job_title: '', whatsapp_number: '', role_id: '' })
      onSuccess()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('dashboard.error.add_user'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    setFormData({ full_name: '', job_title: '', whatsapp_number: '', role_id: '' })
    setError('')
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={t('dashboard.modal.add_title')} size="md">
      <form onSubmit={handleSubmit}>
        <div className="space-y-4">
          <Input
            label={t('dashboard.modal.fullname')}
            placeholder={t('dashboard.modal.fullname_ph')}
            required
            value={formData.full_name}
            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
          />

          <Input
            label={t('dashboard.modal.jobtitle')}
            placeholder={t('dashboard.modal.jobtitle_ph')}
            value={formData.job_title}
            onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
          />

          <Input
            label={t('dashboard.modal.whatsapp')}
            type="tel"
            placeholder="+1234567890"
            required
            value={formData.whatsapp_number}
            onChange={(e) => setFormData({ ...formData, whatsapp_number: e.target.value })}
          />

          <Select
            label={t('dashboard.modal.role')}
            placeholder={t('dashboard.modal.role_ph')}
            required
            value={formData.role_id}
            onChange={(e) => setFormData({ ...formData, role_id: e.target.value })}
            options={roles.map((role: Role) => ({ value: role.id, label: role.name }))}
          />

          {error && <Alert variant="error">{error}</Alert>}

          <div className="flex gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={handleClose} className="flex-1">
              {t('common.cancel')}
            </Button>
            <Button type="submit" isLoading={isLoading} className="flex-1">
              {isLoading ? t('dashboard.modal.btn_loading') : t('dashboard.modal.btn')}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  )
}
