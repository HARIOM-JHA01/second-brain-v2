# React + Vite Migration Plan for Second Brain

> **Implementation Status**: ✅ All Phases Complete

## Overview

**Migration Type**: Staged + Parallel Running  
**Frontend Stack**: React 18 + Vite + TypeScript + Tailwind CSS + React Router + React Query + Recharts  
**Backend**: FastAPI (unchanged, API-only mode)  
**Route Prefix**: `/app/`  
**Timeline**: ~2 weeks for MVP, ~3-4 weeks for full migration

---

## Architecture

```
FastAPI Backend
├── /api/*           → API endpoints (unchanged)
├── /auth/*          → Auth endpoints (unchanged)
├── /static/*        → Static files (images, logos)
├── /                → Landing page (unchanged)
├── /login, /signup  → Old Jinja2 (to be deprecated)
├── /dashboard/*     → Old Jinja2 (to be deprecated)
├── /admin/*         → Old Jinja2 (to be deprecated)
└── /app/*           → NEW React frontend

frontend/
├── src/
│   ├── api/           → API client layer
│   ├── components/    → Reusable UI components
│   ├── contexts/      → Auth, Theme, I18n contexts
│   ├── hooks/         → Custom React hooks
│   ├── pages/         → Page components
│   ├── pages/admin/   → Admin pages
│   ├── locales/       → i18n translation files
│   ├── lib/           → Utilities
│   └── types/         → TypeScript types
└── dist/              → Build output
```

---

## Phases

### Phase 1: Project Scaffolding (Day 1-2)

#### 1.1 Create Directory Structure

```
frontend/
├── public/
├── src/
│   ├── api/
│   │   ├── client.ts
│   │   ├── auth.ts
│   │   ├── users.ts
│   │   ├── roles.ts
│   │   └── admin.ts
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   └── Alert.tsx
│   │   ├── layout/
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── AppLayout.tsx
│   │   └── charts/
│   │       ├── LineChart.tsx
│   │       ├── BarChart.tsx
│   │       └── DonutChart.tsx
│   ├── contexts/
│   │   ├── AuthContext.tsx
│   │   └── ThemeContext.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useTheme.ts
│   │   └── useApi.ts
│   ├── pages/
│   │   ├── auth/
│   │   │   └── AuthPage.tsx
│   │   ├── dashboard/
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── StatsPills.tsx
│   │   │   ├── ChartCard.tsx
│   │   │   ├── UsersTable.tsx
│   │   │   └── AddUserModal.tsx
│   │   ├── users/
│   │   │   └── UsersPage.tsx
│   │   ├── documents/
│   │   │   └── DocumentsPage.tsx
│   │   ├── scenarios/
│   │   │   └── ScenariosPage.tsx
│   │   ├── settings/
│   │   │   └── SettingsPage.tsx
│   │   └── admin/
│   │       ├── AdminDashboard.tsx
│   │       ├── AdminOrganizations.tsx
│   │       ├── AdminUsers.tsx
│   │       └── AdminScenarios.tsx
│   ├── locales/
│   │   ├── es.json
│   │   └── en.json
│   ├── lib/
│   │   └── utils.ts
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   ├── main.tsx
│   ├── index.css
│   └── i18n.ts
│   │   ├── useAuth.ts
│   │   ├── useTheme.ts
│   │   └── useApi.ts
│   ├── pages/
│   │   ├── auth/
│   │   │   └── AuthPage.tsx
│   │   ├── dashboard/
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── StatsPills.tsx
│   │   │   ├── ChartCard.tsx
│   │   │   ├── UsersTable.tsx
│   │   │   └── AddUserModal.tsx
│   │   ├── users/
│   │   │   └── UsersPage.tsx
│   │   ├── documents/
│   │   │   └── DocumentsPage.tsx
│   │   ├── scenarios/
│   │   │   └── ScenariosPage.tsx
│   │   └── settings/
│   │       └── SettingsPage.tsx
│   ├── pages/admin/
│   │   ├── AdminDashboard.tsx
│   │   ├── AdminOrganizations.tsx
│   │   ├── AdminUsers.tsx
│   │   └── AdminScenarios.tsx
│   ├── locales/
│   │   ├── es.json
│   │   └── en.json
│   ├── lib/
│   │   └── utils.ts
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

#### 1.2 Initialize Vite Project

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install react-router-dom @tanstack/react-query react-i18next recharts lucide-react clsx
npm install -D tailwindcss postcss autoprefixer @types/node
npx tailwindcss init -p
```

#### 1.3 Configuration Files

**vite.config.ts**:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
```

**tailwind.config.js**:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#dc2626',
        secondary: '#991b1b',
        background: {
          DEFAULT: 'var(--bg)',
          alt: 'var(--bg-alt)',
        },
        surface: 'var(--surface)',
        border: 'var(--border)',
        text: {
          DEFAULT: 'var(--text)',
          dim: 'var(--text-dim)',
          muted: 'var(--text-muted)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

---

### Phase 2: Core Infrastructure (Day 2-3)

#### 2.1 Type Definitions (`src/types/index.ts`)

```typescript
export interface User {
  id: string;
  email: string;
  full_name: string;
  username: string;
  job_title?: string;
  whatsapp_number: string;
  is_active: boolean;
  created_at: string;
  role?: Role;
}

export interface Role {
  id: string;
  name: string;
  permissions: string[];
}

export interface Organization {
  id: string;
  name: string;
  created_at: string;
}

export interface DashboardStats {
  org_name: string;
  total_users: number;
  active_users: number;
  inactive_users: number;
  new_users_7d: number;
  new_users_30d: number;
  total_docs: number;
  messages_7d: number;
  messages_30d: number;
  avg_response_ms: number;
  messages_chart: { day: string; count: number }[];
  signups_chart: { day: string; count: number }[];
  message_types_breakdown: {
    text: number;
    audio: number;
    image: number;
    document: number;
  };
}

export interface AdminStats {
  total_organizations: number;
  total_users: number;
  active_users: number;
  scenarios_count: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: 'bearer';
}
```

#### 2.2 API Client (`src/api/client.ts`)

```typescript
const API_BASE = '/api';
const AUTH_BASE = '/auth';

interface FetchOptions extends RequestInit {
  requiresAuth?: boolean;
}

async function apiClient<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { requiresAuth = true, ...fetchOptions } = options;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (requiresAuth) {
    const token = localStorage.getItem('access_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...fetchOptions,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem('access_token');
    window.location.href = '/app/login';
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export { apiClient, API_BASE, AUTH_BASE };
```

#### 2.3 Auth API (`src/api/auth.ts`)

```typescript
import { AUTH_BASE } from './client';

interface LoginRequest {
  email: string;
  password: string;
}

interface SignupRequest {
  full_name: string;
  job_title: string;
  email: string;
  whatsapp_number: string;
  organization_name: string;
  password: string;
}

export async function login(data: LoginRequest) {
  const response = await fetch(`${AUTH_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }
  
  return response.json();
}

export async function signup(data: SignupRequest) {
  const response = await fetch(`${AUTH_BASE}/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Signup failed');
  }
  
  return response.json();
}

export async function logout() {
  await fetch(`${AUTH_BASE}/logout`, { method: 'POST' });
  localStorage.removeItem('access_token');
}

export async function getCurrentUser() {
  const token = localStorage.getItem('access_token');
  const response = await fetch(`${AUTH_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  
  if (!response.ok) {
    throw new Error('Failed to get user');
  }
  
  return response.json();
}
```

#### 2.4 Users API (`src/api/users.ts`)

```typescript
import { apiClient } from './client';
import type { User, DashboardStats } from '../types';

export async function getUsers(): Promise<User[]> {
  return apiClient('/users');
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiClient('/users/dashboard-stats');
}

export async function createUser(data: Partial<User>) {
  return apiClient('/users', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateUser(userId: string, data: Partial<User>) {
  return apiClient(`/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteUser(userId: string) {
  return apiClient(`/users/${userId}`, {
    method: 'DELETE',
  });
}

export async function getDocuments() {
  return apiClient('/users/documents');
}
```

#### 2.5 Roles API (`src/api/roles.ts`)

```typescript
import { apiClient } from './client';
import type { Role } from '../types';

export async function getRoles(): Promise<Role[]> {
  return apiClient('/roles');
}

export async function createRole(data: Partial<Role>) {
  return apiClient('/roles', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateRole(roleId: string, data: Partial<Role>) {
  return apiClient(`/roles/${roleId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteRole(roleId: string) {
  return apiClient(`/roles/${roleId}`, {
    method: 'DELETE',
  });
}
```

#### 2.6 Admin API (`src/api/admin.ts`)

```typescript
import { apiClient } from './client';
import type { AdminStats } from '../types';

export async function getAdminStats(): Promise<AdminStats> {
  return apiClient('/admin/api/stats');
}

export async function getOrganizations() {
  return apiClient('/admin/api/organizations');
}

export async function getAdminUsers() {
  return apiClient('/admin/api/users');
}

export async function setUserPassword(userId: string, password: string) {
  return apiClient(`/admin/api/users/${userId}/set-password`, {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

export async function toggleUserActive(profileId: string, isActive: boolean) {
  return apiClient(`/admin/api/users/${profileId}/active`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  });
}

export async function getScenarios() {
  return apiClient('/admin/api/scenarios');
}

export async function createScenario(data: any) {
  return apiClient('/admin/api/scenarios', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateScenario(scenarioId: string, data: any) {
  return apiClient(`/admin/api/scenarios/${scenarioId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteScenario(scenarioId: string) {
  return apiClient(`/admin/api/scenarios/${scenarioId}`, {
    method: 'DELETE',
  });
}
```

#### 2.7 Auth Context (`src/contexts/AuthContext.tsx`)

```typescript
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { login as apiLogin, logout as apiLogout, getCurrentUser } from '@/api/auth';

interface User {
  id: string;
  email: string;
  full_name: string;
  organization_id?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      getCurrentUser()
        .then(setUser)
        .catch(() => localStorage.removeItem('access_token'))
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const data = await apiLogin({ email, password });
    localStorage.setItem('access_token', data.access_token);
    const userData = await getCurrentUser();
    setUser(userData);
  };

  const logout = async () => {
    await apiLogout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

#### 2.8 Theme Context (`src/contexts/ThemeContext.tsx`)

```typescript
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem('sb-theme') as Theme;
    return stored || 'dark';
  });

  useEffect(() => {
    localStorage.setItem('sb-theme', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
```

---

### Phase 3: i18n Migration (Day 3-4)

#### 3.1 Locale Files

**src/locales/es.json** - Spanish translations (migrated from i18n.js)
**src/locales/en.json** - English translations (migrated from i18n.js)

#### 3.2 i18n Configuration (`src/i18n.ts`)

```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import es from './locales/es.json';
import en from './locales/en.json';

const savedLang = localStorage.getItem('sb-lang') || 'es';

i18n
  .use(initReactI18next)
  .init({
    resources: {
      es: { translation: es },
      en: { translation: en },
    },
    lng: savedLang,
    fallbackLng: 'es',
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
```

---

### Phase 4: UI Components (Day 4-5)

| Component | File | Description |
|-----------|------|-------------|
| Button | `components/ui/Button.tsx` | Primary, secondary, danger variants with loading state |
| Input | `components/ui/Input.tsx` | Text input with label, error, icon support |
| Select | `components/ui/Select.tsx` | Dropdown select with options |
| Modal | `components/ui/Modal.tsx` | Dialog overlay with header, body, footer |
| Badge | `components/ui/Badge.tsx` | Status badges (active/inactive) |
| Card | `components/ui/Card.tsx` | Card container with header support |
| Skeleton | `components/ui/Skeleton.tsx` | Loading skeleton |
| Alert | `components/ui/Alert.tsx` | Success/error alerts |
| Navbar | `components/layout/Navbar.tsx` | Top navigation |
| Sidebar | `components/layout/Sidebar.tsx` | Left navigation |
| AppLayout | `components/layout/AppLayout.tsx` | Layout wrapper |

---

### Phase 5: Page Migration (Day 5-10)

#### 5.1 User Pages

| Priority | Page | Components | Time |
|----------|------|-----------|------|
| 1 | Login/Signup | `AuthPage` | 1.5 days |
| 2 | Dashboard | `DashboardPage`, charts, table, modals | 2 days |
| 3 | Users | `UsersPage`, user modals | 1 day |
| 4 | Documents | `DocumentsPage`, upload modal | 1 day |
| 5 | Scenarios | `ScenariosPage` | 0.5 day |
| 6 | Settings | `SettingsPage` | 0.5 day |

#### 5.2 Admin Pages

| Priority | Page | Components | Time |
|----------|------|-----------|------|
| 7 | Admin Dashboard | `AdminDashboard`, stats cards | 1 day |
| 8 | Admin Organizations | `AdminOrganizations`, CRUD | 0.5 day |
| 9 | Admin Users | `AdminUsers`, set password modal | 1 day |
| 10 | Admin Scenarios | `AdminScenarios`, CRUD | 1 day |

---

### Phase 6: Routing (Day 10-12)

#### 6.1 App Router (`src/App.tsx`)

```typescript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import AuthPage from './pages/auth/AuthPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import UsersPage from './pages/users/UsersPage';
import DocumentsPage from './pages/documents/DocumentsPage';
import ScenariosPage from './pages/scenarios/ScenariosPage';
import SettingsPage from './pages/settings/SettingsPage';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminOrganizations from './pages/admin/AdminOrganizations';
import AdminUsers from './pages/admin/AdminUsers';
import AdminScenarios from './pages/admin/AdminScenarios';
import AppLayout from './components/layout/AppLayout';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) return <div>Cargando…</div>;
  return isAuthenticated ? <>{children}</> : <Navigate to="/app/login" />;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/app/login" element={<AuthPage />} />
              
              <Route path="/app" element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }>
                <Route index element={<Navigate to="/app/dashboard" />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="users" element={<UsersPage />} />
                <Route path="documents" element={<DocumentsPage />} />
                <Route path="scenarios" element={<ScenariosPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="admin" element={<AdminDashboard />} />
                <Route path="admin/organizations" element={<AdminOrganizations />} />
                <Route path="admin/users" element={<AdminUsers />} />
                <Route path="admin/scenarios" element={<AdminScenarios />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
```

---

### Phase 7: FastAPI Integration (Day 12-13)

#### 7.1 React Routes in FastAPI

Added to `agente_rolplay/main.py`:

```python
REACT_DIST_DIR = "agente_rolplay/static/react"


def get_react_file_path(full_path: str) -> str:
    if not full_path.startswith("app/"):
        full_path = f"app/{full_path}"
    file_path = os.path.join(REACT_DIST_DIR, full_path)
    if os.path.isfile(file_path):
        return file_path
    index_html = os.path.join(REACT_DIST_DIR, "index.html")
    if os.path.isfile(index_html):
        return index_html
    return None


@app.get("/app/{path:path}")
async def serve_react_app(path: str):
    file_path = get_react_file_path(path)
    if file_path:
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/app")
async def serve_react_app_root():
    index_path = os.path.join(REACT_DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="React app not found")
```

#### 7.2 Copy Build to Static

```bash
# After npm run build
cp -r frontend/dist/* agente_rolplay/static/react/
```

---

### Phase 8: Deployment (Day 13-14)

#### 8.1 Build Commands

**package.json scripts**:
```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "copy-build": "cp -r dist/* ../agente_rolplay/static/react/"
  }
}
```

#### 8.2 Deployment Steps

```bash
# 1. Build React app
cd frontend
npm run build

# 2. Copy to backend static
npm run copy-build

# 3. Start server
uv run uvicorn agente_rolplay.main:app --reload --host 0.0.0.0
```

---

## Route Mapping

| Old Route (Jinja2) | New Route (React) | Status |
|--------------------|-------------------|--------|
| `/login` | `/app/login` | ✅ Migrated |
| `/signup` | `/app/login` | ✅ Migrated |
| `/dashboard` | `/app/dashboard` | ✅ Migrated |
| `/dashboard/users` | `/app/users` | ✅ Migrated |
| `/dashboard/documents` | `/app/documents` | ✅ Migrated |
| `/dashboard/scenarios` | `/app/scenarios` | ✅ Migrated |
| `/dashboard/settings` | `/app/settings` | ✅ Migrated |
| `/admin` | `/app/admin` | ✅ Migrated |
| `/admin/organizations` | `/app/admin/organizations` | ✅ Migrated |
| `/admin/users` | `/app/admin/users` | ✅ Migrated |
| `/admin/scenarios` | `/app/admin/scenarios` | Migrate |

---

## Timeline Summary

| Phase | Days | Deliverable |
|-------|------|-------------|
| Phase 1: Scaffolding | 1-2 | Project structure, Vite, Tailwind |
| Phase 2: Infrastructure | 2-3 | Types, API clients, contexts |
| Phase 3: i18n | 3-4 | Translations migrated |
| Phase 4: Components | 4-5 | UI component library |
| Phase 5: User Pages | 5-8 | Login, Dashboard, Users, Docs, Settings |
| Phase 6: Admin Pages | 8-10 | Admin panel |
| Phase 7: Routing | 10-12 | React Router, FastAPI integration |
| Phase 8: Deploy | 12-14 | Build, copy, test |

**Total: ~2 weeks**

---

## Migration Checklist

### Phase 1: Scaffolding
- [x] Create `frontend/` directory
- [x] Initialize Vite + React + TypeScript
- [x] Install dependencies
- [x] Configure TypeScript
- [x] Configure Tailwind CSS
- [x] Configure Vite proxy

### Phase 2: Core Infrastructure
- [x] Create type definitions (`src/types/index.ts`)
- [x] Implement API client (`src/api/client.ts`)
- [x] Create auth API functions (`src/api/auth.ts`)
- [x] Create users API functions (`src/api/users.ts`)
- [x] Create roles API functions (`src/api/roles.ts`)
- [x] Create admin API functions (`src/api/admin.ts`)
- [x] Implement AuthContext
- [x] Implement ThemeContext

### Phase 3: i18n
- [x] Export translations from `i18n.js`
- [x] Create `src/locales/es.json`
- [x] Create `src/locales/en.json`
- [x] Configure react-i18next
- [x] Update language persistence

### Phase 4: UI Components
- [x] Button component
- [x] Input component
- [x] Select component
- [x] Modal component
- [x] Badge component
- [x] Card component
- [x] Skeleton component
- [x] Alert component
- [x] Navbar component
- [x] Sidebar component
- [x] AppLayout component
- [x] Chart components (Line, Bar, Donut)

### Phase 5: User Pages
- [x] Login/Signup page (AuthPage)
- [x] Dashboard page
- [x] Users page
- [x] Documents page
- [x] Scenarios page
- [x] Settings page

### Phase 6: Admin Pages
- [x] Admin Dashboard
- [x] Admin Organizations
- [x] Admin Users
- [x] Admin Scenarios

### Phase 7: Routing
- [x] Set up React Router
- [x] Create protected route wrapper
- [x] Integrate all pages
- [x] Update FastAPI to serve React app

### Phase 8: Testing & Deployment
- [ ] Test all user pages
- [ ] Test all admin pages
- [ ] Test authentication flow
- [ ] Test theme switching
- [ ] Test language switching
- [ ] Build for production
- [ ] Deploy and verify

---

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Routing | React Router v6 | Standard, well-supported |
| Data Fetching | React Query | Caching, loading states, refetching |
| Charts | Recharts | React-native, customizable |
| Icons | Lucide React | Clean, modern icons |
| Styling | Tailwind CSS | Fast development, consistent design |
| i18n | react-i18next | Industry standard for React |
| Auth Storage | localStorage | Consistent with existing implementation |
| API Client | Custom fetch wrapper | Simple, typed, no extra dependencies |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Admin auth uses sessions, not JWT | Medium | Use session storage for admin routes |
| Chart migration from Chart.js to Recharts | Low | Similar API, straightforward conversion |
| i18n key changes | Medium | Comprehensive testing of both languages |
| Parallel running complexity | Low | Clear route separation (`/app/*` vs `/`) |
