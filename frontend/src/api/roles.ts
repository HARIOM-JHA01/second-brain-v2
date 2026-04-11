import { apiClient } from './client'
import type { Role } from '@/types'

export async function getRoles(): Promise<Role[]> {
  return apiClient('/roles')
}

export async function getRole(roleId: string): Promise<Role> {
  return apiClient(`/roles/${roleId}`)
}

export async function createRole(data: Partial<Role>): Promise<Role> {
  return apiClient('/roles', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateRole(roleId: string, data: Partial<Role>): Promise<Role> {
  return apiClient(`/roles/${roleId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteRole(roleId: string): Promise<void> {
  return apiClient(`/roles/${roleId}`, {
    method: 'DELETE',
  })
}
