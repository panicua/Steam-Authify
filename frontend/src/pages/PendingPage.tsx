import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth'
import { auth } from '@/lib/api'
import { Clock } from 'lucide-react'

export default function PendingPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [name, setName] = useState('')

  useEffect(() => {
    const raw = sessionStorage.getItem('steam_pending_tg')
    if (!raw) {
      navigate('/login', { replace: true })
      return
    }

    const tgData = JSON.parse(raw)
    setName(tgData.first_name || tgData.username || '')

    const interval = setInterval(async () => {
      try {
        const { data } = await auth.telegram(tgData)
        if (data.is_active && data.access_token) {
          sessionStorage.removeItem('steam_pending_tg')
          login(data.access_token, {
            id: data.user_id,
            username: tgData.username || `tg_${tgData.id}`,
            role: data.role,
            is_active: true,
            telegram_username: tgData.username,
            telegram_first_name: tgData.first_name,
            telegram_photo_url: tgData.photo_url,
          })
          navigate('/', { replace: true })
        }
      } catch {
        // ignore — will retry on next interval
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [navigate, login])

  const handleLogout = () => {
    sessionStorage.removeItem('steam_pending_tg')
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
            Hi{name ? ` ${name}` : ''}! Your account has been created but needs
            admin approval before you can access the dashboard.
          </p>
          <p className="text-xs text-muted-foreground/50">
            This page will update automatically once approved.
          </p>
          <Button variant="outline" onClick={handleLogout} className="w-full">
            Back to login
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
