export interface User {
  id: string
  email: string
  full_name: string
  username: string
  job_title?: string
  whatsapp_number: string
  is_active: boolean
  created_at: string
  role?: Role
  organization_id?: string
}

export interface Role {
  id: string
  name: string
  permissions: string[]
  organization_id?: string
  created_at?: string
}

export interface Organization {
  id: string
  name: string
  created_at: string
  owner_id?: string
  settings?: Record<string, unknown>
}

export interface DashboardStats {
  org_name: string
  total_users: number
  active_users: number
  inactive_users: number
  new_users_7d: number
  new_users_30d: number
  total_roles: number
  total_docs: number
  messages_7d: number
  messages_30d: number
  voice_notes_7d: number
  truly_active_users_7d: number
  avg_response_ms: number
  docs_uploaded_7d: number
  docs_uploaded_30d: number
  messages_chart: ChartDataPoint[]
  signups_chart: ChartDataPoint[]
  message_types_breakdown: MessageTypesBreakdown
}

export interface ChartDataPoint {
  day: string
  count: number
}

export interface MessageTypesBreakdown {
  text: number
  audio: number
  image: number
  document: number
}

export interface AdminStats {
  total_organizations: number
  total_users: number
  active_users: number
  scenarios_count: number
}

export interface AuthResponse {
  access_token: string
  token_type: 'bearer'
}

export interface LoginRequest {
  email: string
  password: string
}

export interface SignupRequest {
  full_name: string
  job_title: string
  email: string
  whatsapp_number: string
  organization_name: string
  password: string
}

export interface CreateUserRequest {
  full_name: string
  job_title?: string
  whatsapp_number: string
  role_id: string
  username?: string
  user_id?: string
  org_id?: string
}

export interface Document {
  id: string
  filename: string
  file_url: string
  file_type: string
  file_size: number
  uploaded_by: string
  uploaded_at: string
  organization_id: string
}

export interface Scenario {
  id: string
  name: string
  description: string
  created_at: string
  organization_id: string
  status?: 'active' | 'inactive'
}

export interface ApiError {
  detail: string | Array<{ msg: string; loc: string[]; type: string }>
}
