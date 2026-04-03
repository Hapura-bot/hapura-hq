import { useState, useEffect } from 'react'
import { onAuthStateChanged, signInWithPopup, signOut as fbSignOut, type User } from 'firebase/auth'
import { auth, googleProvider } from '../firebase'

const ALLOWED_EMAILS = new Set([
  'unithree3@gmail.com',
  'dogiatrunghieu123@gmail.com',
  'hapuragroup@gmail.com',
])

export function useAuth() {
  const [user, setUser]       = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, async (u) => {
      if (u && !ALLOWED_EMAILS.has(u.email ?? '')) {
        await fbSignOut(auth)
        setUser(null)
      } else {
        setUser(u)
      }
      setLoading(false)
    })
    return unsub
  }, [])

  const signInWithGoogle = async () => {
    const result = await signInWithPopup(auth, googleProvider)
    if (!ALLOWED_EMAILS.has(result.user.email ?? '')) {
      await fbSignOut(auth)
      throw new Error('UNAUTHORIZED')
    }
    return result
  }

  const signOut = () => fbSignOut(auth)

  return { user, loading, signInWithGoogle, signOut }
}
