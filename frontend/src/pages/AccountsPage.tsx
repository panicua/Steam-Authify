import { useEffect, useState, useRef, useCallback } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from '@/components/ui/dialog'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import PageHeader from '@/components/layout/PageHeader'
import SteamCode from '@/components/SteamCode'
import { accounts } from '@/lib/api'
import { Plus, Trash2, KeyRound, Shield, LogIn } from 'lucide-react'
import { toast } from 'sonner'
import SteamLoginDialog from '@/components/SteamLoginDialog'

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

export default function AccountsPage() {
  const [accountList, setAccountList] = useState<SteamAccount[]>([])
  const [codes, setCodes] = useState<Record<number, CodeState>>({})
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // Steam login dialog
  const [loginAccount, setLoginAccount] = useState<SteamAccount | null>(null)

  // Manual form
  const [accountName, setAccountName] = useState('')
  const [sharedSecret, setSharedSecret] = useState('')

  // File upload
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadAccounts()
  }, [])

  const loadAccounts = async () => {
    try {
      const { data } = await accounts.list()
      setAccountList(data)
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

  const handleManualSubmit = async () => {
    if (!accountName.trim() || !sharedSecret.trim()) return
    setSubmitting(true)
    try {
      await accounts.create({
        account_name: accountName.trim(),
        shared_secret: sharedSecret.trim(),
      })
      toast.success('Account added')
      setAccountName('')
      setSharedSecret('')
      setDialogOpen(false)
      loadAccounts()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Failed to add account')
    } finally {
      setSubmitting(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setSubmitting(true)
    try {
      await accounts.upload(file)
      toast.success('Account added from .maFile')
      setDialogOpen(false)
      loadAccounts()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Failed to upload .maFile')
    } finally {
      setSubmitting(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await accounts.delete(id)
      toast.success('Account removed')
      setCodes((prev) => {
        const next = { ...prev }
        delete next[id]
        return next
      })
      loadAccounts()
    } catch {
      toast.error('Failed to delete account')
    }
  }

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading...</div>
  }

  return (
    <>
      <PageHeader title="Steam Accounts" description="Manage your stored Steam accounts">
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger
            render={<Button size="sm" className="gap-2" />}
          >
            <Plus className="h-4 w-4" /> Add Account
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Steam Account</DialogTitle>
            </DialogHeader>
            <Tabs defaultValue="manual">
              <TabsList className="w-full">
                <TabsTrigger value="manual" className="flex-1">Manual</TabsTrigger>
                <TabsTrigger value="upload" className="flex-1">Upload .maFile</TabsTrigger>
              </TabsList>
              <TabsContent value="manual" className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label htmlFor="account_name">Account Name</Label>
                  <Input
                    id="account_name"
                    placeholder="e.g. my_steam_account"
                    value={accountName}
                    onChange={(e) => setAccountName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="shared_secret">Shared Secret</Label>
                  <Input
                    id="shared_secret"
                    placeholder="Base64-encoded shared secret"
                    value={sharedSecret}
                    onChange={(e) => setSharedSecret(e.target.value)}
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <DialogClose
                    render={<Button variant="outline" />}
                  >
                    Cancel
                  </DialogClose>
                  <Button onClick={handleManualSubmit} disabled={submitting}>
                    {submitting ? 'Adding...' : 'Add Account'}
                  </Button>
                </div>
              </TabsContent>
              <TabsContent value="upload" className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label>Select .maFile</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      ref={fileRef}
                      type="file"
                      accept=".maFile,.json"
                      onChange={handleFileUpload}
                      disabled={submitting}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Upload your Steam Guard .maFile (JSON format). The shared_secret and other fields will be extracted automatically.
                  </p>
                </div>
                {submitting && (
                  <p className="text-sm text-muted-foreground">Uploading...</p>
                )}
              </TabsContent>
            </Tabs>
          </DialogContent>
        </Dialog>
      </PageHeader>

      {accountList.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <Shield className="h-12 w-12 text-muted-foreground" />
            <p className="text-muted-foreground">No accounts yet. Add one to get started.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {accountList.map((account) => (
            <Card key={account.id}>
              <CardContent className="flex items-center justify-between py-4">
                <div className="flex items-center gap-4">
                  <div>
                    <p className="font-medium">{account.account_name}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      {account.steam_id && <span>ID: {account.steam_id}</span>}
                      {account.has_identity_secret && (
                        <span className="rounded bg-muted px-1.5 py-0.5">trade-ready</span>
                      )}
                      {account.has_identity_secret && (
                        <span className="flex items-center gap-1">
                          <span
                            className={`inline-block h-2 w-2 rounded-full ${
                              account.has_session ? 'bg-green-500' : 'bg-gray-400'
                            }`}
                          />
                          {account.has_session ? 'session active' : 'no session'}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {account.has_identity_secret && !account.has_session && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2"
                      onClick={() => setLoginAccount(account)}
                    >
                      <LogIn className="h-4 w-4" />
                      Log In
                    </Button>
                  )}
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
                  <AlertDialog>
                    <AlertDialogTrigger
                      render={<Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" />}
                    >
                      <Trash2 className="h-4 w-4" />
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete account?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This will permanently remove "{account.account_name}" and its stored secrets.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => handleDelete(account.id)}>
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <SteamLoginDialog
        open={!!loginAccount}
        onOpenChange={(open) => !open && setLoginAccount(null)}
        accountId={loginAccount?.id ?? 0}
        accountName={loginAccount?.account_name ?? ''}
        onSuccess={loadAccounts}
      />
    </>
  )
}
