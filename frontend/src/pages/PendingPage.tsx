import { useEffect } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth'
import { auth } from '@/lib/api'
import { Clock } from 'lucide-react'

export default function PendingPage() {
  const { user, isAuthenticated, updateUser, logout } = useAuth()
  const navigate = useNavigate()

  if (!isAuthenticated) return <Navigate to="/login" replace />

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const { data } = await auth.me()
        if (data.is_active) {
          updateUser({
            id: data.id,
            username: data.username,
            role: data.role,
            is_active: data.is_active,
            telegram_username: data.telegram_username,
            telegram_first_name: data.telegram_first_name,
            telegram_photo_url: data.telegram_photo_url,
          })
          navigate('/', { replace: true })
        }
      } catch {
        // ignore
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [updateUser, navigate])

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm text-center">
        <CardHeader>
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            <Clock className="h-6 w-6 text-muted-foreground" />
          </div>
          <CardTitle className="text-xl">Account Pending</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Hi {user?.telegram_first_name || user?.username}! Your account has
            been created but needs admin approval before you can access the
            dashboard.
          </p>
          <p className="text-xs text-muted-foreground/50">
            This page will update automatically once approved.
          </p>
          <Button variant="outline" onClick={handleLogout} className="w-full">
            Sign out
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
