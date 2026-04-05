import { useEffect, useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
import { users } from '@/lib/api'
import { Trash2 } from 'lucide-react'
import { toast } from 'sonner'

interface User {
  id: number
  username: string
  telegram_id: number | null
  role: string
  is_active: boolean
  telegram_username: string | null
  telegram_first_name: string | null
  telegram_photo_url: string | null
  created_at: string
}

export default function UsersPage() {
  const [userList, setUserList] = useState<User[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    try {
      const { data } = await users.list()
      setUserList(data)
    } catch {
      toast.error('Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  const toggleActive = async (user: User) => {
    try {
      await users.update(user.id, { is_active: !user.is_active })
      toast.success(`${user.username} ${user.is_active ? 'deactivated' : 'activated'}`)
      loadUsers()
    } catch {
      toast.error('Failed to update user')
    }
  }

  const changeRole = async (user: User, role: string) => {
    if (role === user.role) return
    try {
      await users.update(user.id, { role })
      toast.success(`${user.username} role changed to ${role}`)
      loadUsers()
    } catch {
      toast.error('Failed to update role')
    }
  }

  const handleDelete = async (user: User) => {
    try {
      await users.delete(user.id)
      toast.success(`${user.username} deleted`)
      loadUsers()
    } catch {
      toast.error('Failed to delete user')
    }
  }

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading...</div>
  }

  return (
    <>
      <PageHeader title="Users" description="Manage user accounts and permissions" />

      <div className="space-y-3">
        {userList.map((user) => (
          <Card key={user.id}>
            <CardContent className="flex items-center justify-between py-4">
              <div className="flex items-center gap-3">
                {user.telegram_photo_url ? (
                  <img src={user.telegram_photo_url} alt="" className="h-9 w-9 rounded-full" />
                ) : (
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-muted text-sm font-medium">
                    {(user.telegram_first_name?.[0] || user.username[0]).toUpperCase()}
                  </div>
                )}
                <div>
                  <p className="font-medium">{user.username}</p>
                  <p className="text-xs text-muted-foreground">
                    {user.telegram_username ? `@${user.telegram_username}` : `ID: ${user.telegram_id ?? 'N/A'}`}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  variant={user.is_active ? 'outline' : 'default'}
                  size="sm"
                  onClick={() => toggleActive(user)}
                >
                  {user.is_active ? 'Deactivate' : 'Activate'}
                </Button>

                <Select
                  value={user.role}
                  onValueChange={(val) => val && changeRole(user, val)}
                >
                  <SelectTrigger className="w-24">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent alignItemWithTrigger={false}>
                    <SelectItem value="user">User</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>

                <Badge variant={user.is_active ? 'default' : 'secondary'}>
                  {user.is_active ? 'Active' : 'Pending'}
                </Badge>

                <AlertDialog>
                  <AlertDialogTrigger
                    render={<Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" />}
                  >
                    <Trash2 className="h-4 w-4" />
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete user?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will permanently delete "{user.username}" and all their stored Steam accounts.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction onClick={() => handleDelete(user)}>
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
    </>
  )
}
