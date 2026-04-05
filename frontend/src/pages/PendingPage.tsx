import { useNavigate, useLocation } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Clock } from 'lucide-react'

export default function PendingPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const name = (location.state as { name?: string })?.name

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
            Please try logging in again after an admin has approved your account.
          </p>
          <Button
            variant="outline"
            onClick={() => navigate('/login', { replace: true })}
            className="w-full"
          >
            Back to login
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
