import { createContext, useContext, useState, useCallback } from 'react'
import type { ReactNode } from 'react'

interface AuthUser {
  id: number
  username: string
  role: string
  is_active: boolean
  telegram_username?: string
  telegram_first_name?: string
  telegram_photo_url?: string
}

interface AuthContextType {
  user: AuthUser | null
  token: string | null
  isAdmin: boolean
  isAuthenticated: boolean
  isPending: boolean
  login: (token: string, user: AuthUser) => void
  updateUser: (user: AuthUser) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const stored = localStorage.getItem('steam_user')
    return stored ? JSON.parse(stored) : null
  })
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem('steam_token')
  )

  const login = useCallback((newToken: string, newUser: AuthUser) => {
    localStorage.setItem('steam_token', newToken)
    localStorage.setItem('steam_user', JSON.stringify(newUser))
    setToken(newToken)
    setUser(newUser)
  }, [])

  const updateUser = useCallback((newUser: AuthUser) => {
    localStorage.setItem('steam_user', JSON.stringify(newUser))
    setUser(newUser)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('steam_token')
    localStorage.removeItem('steam_user')
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAdmin: user?.role === 'admin',
        isAuthenticated: !!token && !!user,
        isPending: !!user && !user.is_active,
        login,
        updateUser,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
