import { createContext, useContext, useEffect, type ReactNode } from 'react'
import { useAuth } from './hooks/useAuth'
import { setTokenProvider, clearTokenProvider } from './api/client'
import type { User } from 'firebase/auth'

interface AuthContextValue {
  user: User | null
  loading: boolean
  signInWithGoogle: () => Promise<unknown>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const auth = useAuth()
  useEffect(() => {
    if (auth.user) {
      setTokenProvider(() => auth.user!.getIdToken())
    } else {
      clearTokenProvider()
    }
  }, [auth.user])
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>
}

export function useAuthContext() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuthContext must be inside AuthProvider')
  return ctx
}
