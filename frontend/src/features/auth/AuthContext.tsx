// Auth + feature-flag context (PLT-6; CLAUDE.md rule 9: entitlements hidden
// client-side via hasFeature, enforced server-side regardless).
import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { setAccessToken } from '@/api/auth-token'
import { v1AuthLoginCreate, v1AuthLogoutCreate, v1AuthRefreshCreate } from '@/api/generated/api'
import type { UserSummary } from '@/api/generated/model'

interface AuthContextValue {
  user: UserSummary | null
  /** 'restoring' until the silent-refresh attempt on boot settles */
  status: 'restoring' | 'ready'
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hasPermission: (code: string) => boolean
  hasFeature: (code: string) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserSummary | null>(null)
  const [status, setStatus] = useState<'restoring' | 'ready'>('restoring')
  const queryClient = useQueryClient()

  // The httpOnly refresh cookie survives reloads; try to restore the session.
  useEffect(() => {
    v1AuthRefreshCreate()
      .then((response) => {
        setAccessToken(response.access)
        setUser(response.user)
      })
      .catch(() => setAccessToken(null))
      .finally(() => setStatus('ready'))
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const response = await v1AuthLoginCreate({ username, password })
    setAccessToken(response.access)
    setUser(response.user)
  }, [])

  const logout = useCallback(async () => {
    await v1AuthLogoutCreate().catch(() => undefined) // clear locally even if offline
    setAccessToken(null)
    setUser(null)
    queryClient.clear()
  }, [queryClient])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      login,
      logout,
      hasPermission: (code) => user?.permissions.includes(code) ?? false,
      hasFeature: (code) => user?.features.includes(code) ?? false,
    }),
    [user, status, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
