import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import { AppLayout } from './components/layout/AppLayout'
import AuthPage from './pages/auth/AuthPage'
import DashboardPage from './pages/dashboard/DashboardPage'
import UsersPage from './pages/users/UsersPage'
import DocumentsPage from './pages/documents/DocumentsPage'
import ScenariosPage from './pages/scenarios/ScenariosPage'
import SettingsPage from './pages/settings/SettingsPage'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminOrganizations from './pages/admin/AdminOrganizations'
import AdminUsers from './pages/admin/AdminUsers'
import AdminScenarios from './pages/admin/AdminScenarios'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent"></div>
      </div>
    )
  }
  
  return isAuthenticated ? <>{children}</> : <Navigate to="/app/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/app/login" element={<AuthPage />} />
      
      <Route path="/app" element={
        <ProtectedRoute>
          <AppLayout />
        </ProtectedRoute>
      }>
        <Route index element={<Navigate to="/app/dashboard" replace />} />
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

      <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
    </Routes>
  )
}
