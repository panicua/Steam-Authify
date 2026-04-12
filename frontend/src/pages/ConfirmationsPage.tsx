import { useEffect, useState, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import PageHeader from '@/components/layout/PageHeader'
import SteamLoginDialog from '@/components/SteamLoginDialog'
import { accounts, confirmations } from '@/lib/api'
import {
  ArrowLeftRight,
  ShoppingCart,
  HelpCircle,
  CheckCircle,
  XCircle,
  RefreshCw,
  LogIn,
  Shield,
  Loader2,
} from 'lucide-react'
import { toast } from 'sonner'

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

interface ConfirmationItem {
  id: string
  nonce: string
  type: number
  type_name: string
  creator_id: string
  headline: string
  summary: string[]
  icon: string | null
  created_at: string | null
}

interface AccountConfirmations {
  account_id: number
  account_name: string
  confirmations: ConfirmationItem[]
}

function getTypeIcon(type: number) {
  switch (type) {
    case 2:
      return <ArrowLeftRight className="h-5 w-5 text-blue-500" />
    case 3:
      return <ShoppingCart className="h-5 w-5 text-green-500" />
    default:
      return <HelpCircle className="h-5 w-5 text-muted-foreground" />
  }
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

export default function ConfirmationsPage() {
  const [searchParams] = useSearchParams()
  const [accountList, setAccountList] = useState<SteamAccount[]>([])
  const [allConfs, setAllConfs] = useState<AccountConfirmations[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [activeFilter, setActiveFilter] = useState<number | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [loginAccount, setLoginAccount] = useState<SteamAccount | null>(null)
  const [actionLoading, setActionLoading] = useState<Set<string>>(new Set())
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const initialAccountId = searchParams.get('account')
    ? Number(searchParams.get('account'))
    : null

  useEffect(() => {
    if (initialAccountId) setActiveFilter(initialAccountId)
  }, [initialAccountId])

  const tradeReadyAccounts = accountList.filter(
    (a) => a.has_identity_secret && a.steam_id
  )

  const sessionAccounts = tradeReadyAccounts.filter((a) => a.has_session)

  const loadAccounts = useCallback(async () => {
    try {
      const { data } = await accounts.list()
      setAccountList(data)
      return data as SteamAccount[]
    } catch {
      toast.error('Failed to load accounts')
      return []
    }
  }, [])

  const fetchAllConfirmations = useCallback(
    async (accts?: SteamAccount[]) => {
      const list = accts || sessionAccounts
      const results: AccountConfirmations[] = []

      await Promise.allSettled(
        list.map(async (account) => {
          try {
            const { data } = await confirmations.list(account.id)
            results.push(data)
          } catch (err: unknown) {
            const status = (err as { response?: { status?: number } })?.response?.status
            if (status === 401) {
              toast.error(`Session expired for ${account.account_name}`)
            }
          }
        })
      )

      setAllConfs(results)
    },
    [sessionAccounts]
  )

  const loadAll = useCallback(async () => {
    setLoading(true)
    const accts = await loadAccounts()
    const ready = (accts as SteamAccount[]).filter(
      (a) => a.has_identity_secret && a.steam_id && a.has_session
    )
    await fetchAllConfirmations(ready)
    setLoading(false)
  }, [loadAccounts, fetchAllConfirmations])

  useEffect(() => {
    loadAll()
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    const accts = await loadAccounts()
    const ready = (accts as SteamAccount[]).filter(
      (a) => a.has_identity_secret && a.steam_id && a.has_session
    )
    await fetchAllConfirmations(ready)
    setRefreshing(false)
  }

  // Auto-refresh
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(() => {
        if (!document.hidden) handleRefresh()
      }, 30000)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [autoRefresh])

  // Flatten confirmations for display
  const displayConfs: (ConfirmationItem & { account_id: number; account_name: string })[] = []
  for (const ac of allConfs) {
    if (activeFilter && ac.account_id !== activeFilter) continue
    for (const c of ac.confirmations) {
      displayConfs.push({ ...c, account_id: ac.account_id, account_name: ac.account_name })
    }
  }

  const pendingCounts: Record<number, number> = {}
  for (const ac of allConfs) {
    pendingCounts[ac.account_id] = ac.confirmations.length
  }

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === displayConfs.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(displayConfs.map((c) => `${c.account_id}:${c.id}`)))
    }
  }

  const handleAction = async (
    accountId: number,
    confId: string,
    action: 'accept' | 'decline'
  ) => {
    const key = `${accountId}:${confId}`
    setActionLoading((prev) => new Set(prev).add(key))
    try {
      const { data } = action === 'accept'
        ? await confirmations.accept(accountId, confId)
        : await confirmations.decline(accountId, confId)

      if (!data.success) {
        toast.error(
          `Steam rejected this ${action} — the account may have trade restrictions ` +
          `(not friends long enough, limited account, market cooldown, etc.)`
        )
        return
      }

      toast.success(`Confirmation ${action === 'accept' ? 'accepted' : 'declined'}`)
      await handleRefresh()
      setSelectedIds((prev) => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        `Failed to ${action} confirmation`
      toast.error(msg)
    } finally {
      setActionLoading((prev) => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
    }
  }

  const handleBulkAction = async (action: 'accept' | 'decline') => {
    // Group selected by account
    const grouped: Record<number, string[]> = {}
    for (const key of selectedIds) {
      const [accId, confId] = key.split(':')
      const id = Number(accId)
      if (!grouped[id]) grouped[id] = []
      grouped[id].push(confId)
    }

    let succeeded = 0
    let failed = 0
    for (const [accIdStr, confIds] of Object.entries(grouped)) {
      try {
        const { data } = await confirmations.batch(Number(accIdStr), {
          confirmation_ids: confIds,
          action,
        })
        for (const r of data.results) {
          if (r.success) succeeded++
          else failed++
        }
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          `Batch ${action} failed`
        toast.error(msg)
        failed += confIds.length
      }
    }

    if (succeeded > 0) {
      toast.success(`${succeeded} confirmation(s) ${action === 'accept' ? 'accepted' : 'declined'}`)
    }
    if (failed > 0) {
      toast.error(
        `${failed} confirmation(s) rejected by Steam — check account trade restrictions`
      )
    }
    setSelectedIds(new Set())
    await handleRefresh()
  }

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading...</div>
  }

  // Empty state: no trade-ready accounts at all
  if (tradeReadyAccounts.length === 0) {
    return (
      <>
        <PageHeader
          title="Trade Confirmations"
          description="Review and manage pending trade confirmations"
        />
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <Shield className="h-12 w-12 text-muted-foreground" />
            <p className="text-muted-foreground">
              No trade-ready accounts. Add an account with an identity_secret to get started.
            </p>
          </CardContent>
        </Card>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Trade Confirmations"
        description="Review and manage pending trade confirmations"
      >
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="rounded"
          />
          Auto-refresh
        </label>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </PageHeader>

      {/* Account filter pills */}
      <div className="mb-4 flex flex-wrap gap-2">
        <Button
          variant={activeFilter === null ? 'default' : 'outline'}
          size="sm"
          onClick={() => setActiveFilter(null)}
        >
          All Accounts
        </Button>
        {tradeReadyAccounts.map((account) => (
          <Button
            key={account.id}
            variant={activeFilter === account.id ? 'default' : 'outline'}
            size="sm"
            className="gap-2"
            onClick={() =>
              setActiveFilter(activeFilter === account.id ? null : account.id)
            }
          >
            {account.account_name}
            {pendingCounts[account.id] ? (
              <Badge variant="secondary" className="ml-1 px-1.5 py-0 text-xs">
                {pendingCounts[account.id]}
              </Badge>
            ) : null}
            {!account.has_session && (
              <span className="inline-block h-2 w-2 rounded-full bg-amber-400" title="No session" />
            )}
          </Button>
        ))}
      </div>

      {/* Selected account without session — prompt to login */}
      {(() => {
        if (activeFilter === null) return null;
        const selected = tradeReadyAccounts.find((a) => a.id === activeFilter);
        if (!selected || selected.has_session) return null;
        return (
          <Card className="mb-4">
            <CardContent className="flex items-center justify-between py-3">
              <p className="text-sm text-muted-foreground">
                <span className="font-medium text-foreground">{selected.account_name}</span> needs
                a Steam session to view confirmations.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={() => setLoginAccount(selected)}
              >
                <LogIn className="h-4 w-4" />
                Log In
              </Button>
            </CardContent>
          </Card>
        );
      })()}

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className="sticky top-0 z-10 mb-4 flex items-center gap-3 rounded-lg border bg-background p-3 shadow-sm">
          <span className="text-sm font-medium">{selectedIds.size} selected</span>
          <AlertDialog>
            <AlertDialogTrigger
              render={
                <Button size="sm" variant="outline" className="gap-2 border-green-300 text-green-700 hover:bg-green-50 dark:border-green-700 dark:text-green-400 dark:hover:bg-green-950" />
              }
            >
              <CheckCircle className="h-4 w-4" />
              Accept Selected
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Accept {selectedIds.size} confirmation(s)?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will accept all selected trade confirmations. This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => handleBulkAction('accept')}>
                  Accept All
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          <AlertDialog>
            <AlertDialogTrigger
              render={
                <Button size="sm" variant="outline" className="gap-2 border-red-300 text-red-700 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-950" />
              }
            >
              <XCircle className="h-4 w-4" />
              Decline Selected
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Decline {selectedIds.size} confirmation(s)?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will decline all selected trade confirmations. This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => handleBulkAction('decline')}>
                  Decline All
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setSelectedIds(new Set())}
          >
            Clear
          </Button>
          <div className="ml-auto">
            <Button size="sm" variant="ghost" onClick={toggleSelectAll}>
              {selectedIds.size === displayConfs.length ? 'Deselect all' : 'Select all'}
            </Button>
          </div>
        </div>
      )}

      {/* Confirmation cards */}
      {displayConfs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <CheckCircle className="h-12 w-12 text-muted-foreground" />
            <p className="text-muted-foreground">No pending confirmations</p>
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
              Refresh
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {displayConfs.map((conf) => {
            const key = `${conf.account_id}:${conf.id}`
            const isSelected = selectedIds.has(key)
            const isLoading = actionLoading.has(key)

            return (
              <Card
                key={key}
                className={isSelected ? 'ring-2 ring-primary' : ''}
              >
                <CardContent className="py-4">
                  <div className="flex items-start gap-4">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelect(key)}
                      className="mt-1 rounded"
                    />
                    <div className="mt-0.5">{getTypeIcon(conf.type)}</div>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{conf.headline || conf.type_name}</p>
                      {conf.summary.length > 0 && (
                        <p className="text-sm text-muted-foreground">
                          {conf.summary.join(' · ')}
                        </p>
                      )}
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <span>Account: {conf.account_name}</span>
                        {conf.created_at && (
                          <>
                            <span>·</span>
                            <span>{timeAgo(conf.created_at)}</span>
                          </>
                        )}
                        <Badge variant="outline" className="text-xs">
                          {conf.type_name}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <AlertDialog>
                        <AlertDialogTrigger
                          render={
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={isLoading}
                              className="gap-2 border-green-300 text-green-700 hover:bg-green-50 dark:border-green-700 dark:text-green-400 dark:hover:bg-green-950"
                            />
                          }
                        >
                          {isLoading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <CheckCircle className="h-4 w-4" />
                          )}
                          Accept
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Accept this confirmation?</AlertDialogTitle>
                            <AlertDialogDescription>
                              {conf.headline}
                              {conf.summary.length > 0 && ` — ${conf.summary.join(', ')}`}.
                              This action cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleAction(conf.account_id, conf.id, 'accept')}
                            >
                              Accept
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                      <AlertDialog>
                        <AlertDialogTrigger
                          render={
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={isLoading}
                              className="gap-2 text-red-600 hover:text-red-700 dark:text-red-400"
                            />
                          }
                        >
                          <XCircle className="h-4 w-4" />
                          Decline
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Decline this confirmation?</AlertDialogTitle>
                            <AlertDialogDescription>
                              {conf.headline}. This action cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleAction(conf.account_id, conf.id, 'decline')}
                            >
                              Decline
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <SteamLoginDialog
        open={!!loginAccount}
        onOpenChange={(open) => !open && setLoginAccount(null)}
        accountId={loginAccount?.id ?? 0}
        accountName={loginAccount?.account_name ?? ''}
        onSuccess={loadAll}
      />
    </>
  )
}
