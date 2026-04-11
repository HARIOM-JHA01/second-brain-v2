import { AUTH_BASE, getToken } from './client'
import type { User, LoginRequest, SignupRequest, AuthResponse } from '@/types'

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const response = await fetch(`${AUTH_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }))
    const message = typeof error.detail === 'string' ? error.detail : 'Login failed'
    throw new Error(message)
  }
  
  return response.json()
}

export async function signup(data: SignupRequest): Promise<AuthResponse & { user_id: string; organization_id: string }> {
  const response = await fetch(`${AUTH_BASE}/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Signup failed' }))
    const message = typeof error.detail === 'string' ? error.detail : 'Signup failed'
    throw new Error(message)
  }
  
  return response.json()
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${AUTH_BASE}/logout`, { method: 'POST' })
  } finally {
    localStorage.removeItem('access_token')
  }
}

export async function getCurrentUser(): Promise<User> {
  const token = getToken()
  const response = await fetch(`${AUTH_BASE}/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  
  if (!response.ok) {
    throw new Error('Failed to get user')
  }
  
  return response.json()
}
