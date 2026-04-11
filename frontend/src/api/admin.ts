import { apiClient } from './client'
import type { AdminStats, Scenario } from '@/types'

interface Organization {
  id: string
  name: string
  created_at: string
  user_count?: number
}

interface AdminUser {
  id: string
  email: string
  full_name: string
  is_active: boolean
  organization_name: string
  created_at: string
}

export async function getAdminStats(): Promise<AdminStats> {
  return apiClient('/admin/api/stats')
}

export async function getOrganizations(): Promise<Organization[]> {
  return apiClient('/admin/api/organizations')
}

export async function getAdminUsers(): Promise<AdminUser[]> {
  return apiClient('/admin/api/users')
}

export async function setUserPassword(userId: string, password: string): Promise<void> {
  return apiClient(`/admin/api/users/${userId}/set-password`, {
    method: 'POST',
    body: JSON.stringify({ password }),
  })
}

export async function toggleUserActive(profileId: string, isActive: boolean): Promise<void> {
  return apiClient(`/admin/api/users/${profileId}/active`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  })
}

export async function deleteAdminUser(userId: string): Promise<void> {
  return apiClient(`/admin/api/users/${userId}`, {
    method: 'DELETE',
  })
}

export async function deleteOrganization(orgId: string): Promise<void> {
  return apiClient(`/admin/api/organizations/${orgId}`, {
    method: 'DELETE',
  })
}

export async function getScenarios(): Promise<Scenario[]> {
  return apiClient('/admin/api/scenarios')
}

export async function createScenario(data: Partial<Scenario>): Promise<Scenario> {
  return apiClient('/admin/api/scenarios', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateScenario(scenarioId: string, data: Partial<Scenario>): Promise<Scenario> {
  return apiClient(`/admin/api/scenarios/${scenarioId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteScenario(scenarioId: string): Promise<void> {
  return apiClient(`/admin/api/scenarios/${scenarioId}`, {
    method: 'DELETE',
  })
}

export async function getScenarioReferenceFiles(scenarioId: string): Promise<unknown[]> {
  return apiClient(`/admin/api/scenarios/${scenarioId}/reference-files`)
}

export async function deleteScenarioReferenceFile(scenarioId: string, fileId: string): Promise<void> {
  return apiClient(`/admin/api/scenarios/${scenarioId}/reference-files/${fileId}`, {
    method: 'DELETE',
  })
}
