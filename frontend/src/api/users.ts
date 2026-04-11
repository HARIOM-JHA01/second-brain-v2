import { apiClient } from './client'
import type { User, DashboardStats, CreateUserRequest, Document } from '@/types'

export async function getUsers(): Promise<User[]> {
  return apiClient('/users')
}

export async function getUser(userId: string): Promise<User> {
  return apiClient(`/users/${userId}`)
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiClient('/users/dashboard-stats')
}

export async function createUser(data: CreateUserRequest): Promise<User> {
  return apiClient('/users', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateUser(userId: string, data: Partial<User>): Promise<User> {
  return apiClient(`/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteUser(userId: string): Promise<void> {
  return apiClient(`/users/${userId}`, {
    method: 'DELETE',
  })
}

export async function reactivateUser(userId: string): Promise<User> {
  return apiClient(`/users/${userId}/reactivate`, {
    method: 'POST',
  })
}

export async function getDocuments(): Promise<Document[]> {
  return apiClient('/users/documents')
}
