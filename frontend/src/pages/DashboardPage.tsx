import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import PageHeader from '@/components/layout/PageHeader'
import SteamCode from '@/components/SteamCode'
import { accounts } from '@/lib/api'
import { Shield, KeyRound, ArrowLeftRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { confirmations } from '@/lib/api'

interface SteamAccount {
  id: number
  account_name: string
  steam_id: number | null
  has_identity_secret: boolean
  has_device_id: boolean
  has_session: boolean
  serial_number: string | null
  created_at: string
}

interface CodeState {
  code: string
  expires_in: number
}

export default function DashboardPage() {
  const [accountList, setAccountList] = useState<SteamAccount[]>([])
  const [codes, setCodes] = useState<Record<number, CodeState>>({})
  const [pendingCounts, setPendingCounts] = useState<Record<number, number>>({})
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    loadAccounts()
  }, [])

  const loadAccounts = async () => {
    try {
      const { data } = await accounts.list()
      setAccountList(data)
      // Fetch pending confirmation counts for session accounts
      const sessionAccounts = (data as SteamAccount[]).filter(
        (a) => a.has_identity_secret && a.has_session && a.steam_id
      )
      const counts: Record<number, number> = {}
      await Promise.allSettled(
        sessionAccounts.map(async (acc) => {
          try {
            const { data: confData } = await confirmations.list(acc.id)
            if (confData.confirmations?.length > 0) {
              counts[acc.id] = confData.confirmations.length
            }
          } catch { /* ignore errors for badge counts */ }
        })
      )
      setPendingCounts(counts)
    } catch {
      toast.error('Failed to load accounts')
    } finally {
      setLoading(false)
    }
  }

  const fetchCode = useCallback(async (accountId: number) => {
    try {
      const { data } = await accounts.getCode(accountId)
      setCodes((prev) => ({ ...prev, [accountId]: data }))
    } catch {
      toast.error('Failed to generate code')
    }
  }, [])

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading...</div>
  }

  return (
    <>
      <PageHeader title="Dashboard" description="Your Steam Guard codes at a glance" />

      {accountList.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <Shield className="h-12 w-12 text-muted-foreground" />
            <p className="text-muted-foreground">No Steam accounts added yet</p>
            <Button onClick={() => navigate('/accounts')}>
              Add Your First Account
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {accountList.map((account) => (
            <Card key={account.id}>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Shield className="h-4 w-4" />
                  {account.account_name}
                  {pendingCounts[account.id] && (
                    <Badge
                      variant="secondary"
                      className="ml-auto cursor-pointer bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900 dark:text-amber-300"
                      onClick={(e) => {
                        e.stopPropagation()
                        navigate(`/confirmations?account=${account.id}`)
                      }}
                    >
                      <ArrowLeftRight className="mr-1 h-3 w-3" />
                      {pendingCounts[account.id]} pending
                    </Badge>
                  )}
                </CardTitle>
                {account.steam_id && (
                  <p className="text-xs text-muted-foreground">
                    {account.steam_id}
                  </p>
                )}
              </CardHeader>
              <CardContent>
                {codes[account.id] ? (
                  <SteamCode
                    code={codes[account.id].code}
                    expiresIn={codes[account.id].expires_in}
                    onExpired={() => fetchCode(account.id)}
                  />
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-2"
                    onClick={() => fetchCode(account.id)}
                  >
                    <KeyRound className="h-4 w-4" />
                    Get Code
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}
