import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import PageHeader from '@/components/layout/PageHeader'
import SteamCode from '@/components/SteamCode'
import { accounts } from '@/lib/api'
import { toast } from 'sonner'

interface CodeState {
  code: string
  expires_in: number
}

export default function GeneratePage() {
  const [sharedSecret, setSharedSecret] = useState('')
  const [codeState, setCodeState] = useState<CodeState | null>(null)
  const [loading, setLoading] = useState(false)

  const handleGenerate = async () => {
    if (!sharedSecret.trim()) return
    setLoading(true)
    try {
      const { data } = await accounts.generate(sharedSecret.trim())
      setCodeState(data)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Failed to generate code')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    if (!sharedSecret.trim()) return
    try {
      const { data } = await accounts.generate(sharedSecret.trim())
      setCodeState(data)
    } catch {
      toast.error('Failed to refresh code')
    }
  }

  return (
    <>
      <PageHeader
        title="Quick Generate"
        description="Generate a Steam Guard code without storing the secret"
      />

      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle className="text-base">Paste your shared_secret</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="secret">Shared Secret (Base64)</Label>
            <Input
              id="secret"
              placeholder="e.g. 3UFrjYQmxdVN5Wt0z8a+Ql1BH5U="
              value={sharedSecret}
              onChange={(e) => setSharedSecret(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
            />
          </div>

          <Button onClick={handleGenerate} disabled={loading || !sharedSecret.trim()}>
            {loading ? 'Generating...' : 'Generate Code'}
          </Button>

          {codeState && (
            <div className="pt-4">
              <SteamCode
                code={codeState.code}
                expiresIn={codeState.expires_in}
                onExpired={handleRefresh}
              />
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            Your secret is sent to the server only to compute the code. Nothing is stored.
          </p>
        </CardContent>
      </Card>
    </>
  )
}
