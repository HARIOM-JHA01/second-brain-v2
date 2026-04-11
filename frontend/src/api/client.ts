export const API_BASE = '/api'
export const AUTH_BASE = '/auth'

export interface ApiClientOptions extends RequestInit {
  requiresAuth?: boolean
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiClient<T>(
  endpoint: string,
  options: ApiClientOptions = {}
): Promise<T> {
  const { requiresAuth = true, ...fetchOptions } = options
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (requiresAuth) {
    const token = localStorage.getItem('access_token')
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...fetchOptions,
    headers,
  })

  if (response.status === 401) {
    localStorage.removeItem('access_token')
    window.location.href = '/app/login'
    throw new ApiError('Unauthorized', 401)
  }

  if (!response.ok) {
    let errorData
    try {
      errorData = await response.json()
    } catch {
      errorData = { detail: 'Unknown error' }
    }
    const message = typeof errorData.detail === 'string' 
      ? errorData.detail 
      : 'Request failed'
    throw new ApiError(message, response.status, errorData)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

export function getToken(): string | null {
  return localStorage.getItem('access_token')
}

export function setToken(token: string): void {
  localStorage.setItem('access_token', token)
}

export function removeToken(): void {
  localStorage.removeItem('access_token')
}
