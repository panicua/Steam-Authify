import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import TelegramLoginButton from '@/components/TelegramLoginButton'
import type { TelegramUser } from '@/components/TelegramLoginButton'
import { useAuth } from '@/lib/auth'
import { auth } from '@/lib/api'

const TG_BOT_NAME = import.meta.env.VITE_TELEGRAM_BOT_NAME || ''

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleTelegramAuth = async (tgUser: TelegramUser) => {
    setError('')
    setLoading(true)
    try {
      const { data } = await auth.telegram({
        id: tgUser.id,
        first_name: tgUser.first_name,
        last_name: tgUser.last_name,
        username: tgUser.username,
        photo_url: tgUser.photo_url,
        auth_date: tgUser.auth_date,
        hash: tgUser.hash,
      })

      if (data.is_active && data.access_token) {
        login(data.access_token, {
          id: data.user_id,
          username: tgUser.username || `tg_${tgUser.id}`,
          role: data.role,
          is_active: data.is_active,
          telegram_username: tgUser.username,
          telegram_first_name: tgUser.first_name,
          telegram_photo_url: tgUser.photo_url,
        })
        navigate('/', { replace: true })
      } else {
        navigate('/pending', {
          replace: true,
          state: { name: tgUser.first_name || tgUser.username },
        })
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Steam Auth</CardTitle>
          <p className="text-sm text-muted-foreground">
            Sign in with your Telegram account
          </p>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          {TG_BOT_NAME ? (
            <TelegramLoginButton
              botName={TG_BOT_NAME}
              onAuth={handleTelegramAuth}
            />
          ) : (
            <p className="text-sm text-destructive">
              VITE_TELEGRAM_BOT_NAME is not configured
            </p>
          )}
          {loading && (
            <p className="text-sm text-muted-foreground">Authenticating...</p>
          )}
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
