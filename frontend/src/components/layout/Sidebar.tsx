import { NavLink } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import {
  Users,
  LayoutDashboard,
  LogOut,
  Shield,
  KeyRound,
  ArrowLeftRight,
} from 'lucide-react'
import ThemeToggle from '@/components/ThemeToggle'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, adminOnly: false },
  { to: '/accounts', label: 'Steam Accounts', icon: Shield, adminOnly: false },
  { to: '/confirmations', label: 'Confirmations', icon: ArrowLeftRight, adminOnly: false },
  { to: '/generate', label: 'Quick Generate', icon: KeyRound, adminOnly: false },
  { to: '/users', label: 'Users', icon: Users, adminOnly: true },
]

export default function Sidebar() {
  const { user, isAdmin, logout } = useAuth()

  const visibleItems = navItems.filter((item) => !item.adminOnly || isAdmin)

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-border bg-sidebar">
      <div className="flex h-14 items-center border-b border-border px-4">
        <h1 className="text-lg font-semibold text-sidebar-foreground">
          Steam Auth
        </h1>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 py-2">
        {visibleItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                  : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-border px-3 py-3">
        <div className="mb-2 flex items-center gap-2 px-1">
          {user?.telegram_photo_url ? (
            <img
              src={user.telegram_photo_url}
              alt=""
              className="h-7 w-7 rounded-full"
            />
          ) : (
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-medium">
              {(user?.telegram_first_name?.[0] || user?.username?.[0] || '?').toUpperCase()}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-sidebar-foreground">
              {user?.telegram_first_name || user?.username}
            </p>
            <p className="truncate text-xs text-sidebar-foreground/50">
              {isAdmin ? 'Admin' : 'User'}
            </p>
          </div>
          <ThemeToggle />
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 text-sidebar-foreground/70"
          onClick={logout}
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </Button>
      </div>
    </aside>
  )
}
