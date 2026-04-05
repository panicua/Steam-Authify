import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/lib/auth'
import { ThemeProvider } from '@/lib/theme'
import AppLayout from '@/components/layout/AppLayout'
import DashboardPage from '@/pages/DashboardPage'
import AccountsPage from '@/pages/AccountsPage'
import GeneratePage from '@/pages/GeneratePage'
import ConfirmationsPage from '@/pages/ConfirmationsPage'
import UsersPage from '@/pages/UsersPage'
import LoginPage from '@/pages/LoginPage'
import PendingPage from '@/pages/PendingPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isPending } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (isPending) return <Navigate to="/pending" replace />
  return <>{children}</>
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { isAdmin } = useAuth()
  if (!isAdmin) return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/pending" element={<PendingPage />} />
            <Route
              element={
                <RequireAuth>
                  <AppLayout />
                </RequireAuth>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="accounts" element={<AccountsPage />} />
              <Route path="confirmations" element={<ConfirmationsPage />} />
              <Route path="generate" element={<GeneratePage />} />
              <Route path="users" element={<RequireAdmin><UsersPage /></RequireAdmin>} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
