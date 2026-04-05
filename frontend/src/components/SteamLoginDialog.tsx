import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2, LogIn } from 'lucide-react'
import { sessions } from '@/lib/api'
import { toast } from 'sonner'

interface SteamLoginDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  accountId: number
  accountName: string
  expired?: boolean
  onSuccess?: () => void
}

export default function SteamLoginDialog({
  open,
  onOpenChange,
  accountId,
  accountName,
  expired,
  onSuccess,
}: SteamLoginDialogProps) {
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!password.trim()) return

    setLoading(true)
    setError(null)
    try {
      await sessions.login(accountId, password)
      toast.success(`Session active for ${accountName}`)
      setPassword('')
      onOpenChange(false)
      onSuccess?.()
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || 'Steam login failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {expired ? 'Session Expired' : 'Log in to Steam'}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {expired
              ? `Session expired for "${accountName}". Enter your password to log in again.`
              : `Enter the Steam password for "${accountName}". Your password is used only to obtain a session and is not stored.`}
          </p>
          <div className="space-y-2">
            <Label htmlFor="steam_password">Steam Password</Label>
            <Input
              id="steam_password"
              type="password"
              placeholder="Enter Steam password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
              disabled={loading}
            />
          </div>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <div className="flex justify-end gap-2">
            <DialogClose
              render={<Button type="button" variant="outline" disabled={loading} />}
            >
              Cancel
            </DialogClose>
            <Button type="submit" disabled={loading || !password.trim()}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Logging in...
                </>
              ) : (
                <>
                  <LogIn className="mr-2 h-4 w-4" />
                  Log In
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
