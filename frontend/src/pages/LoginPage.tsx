import { useState } from 'react'
import { Crosshair, ShieldAlert } from 'lucide-react'
import { useAuthContext } from '../AuthContext'

export default function LoginPage() {
  const { signInWithGoogle } = useAuthContext()
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin() {
    setError('')
    setLoading(true)
    try {
      await signInWithGoogle()
    } catch (e: unknown) {
      if (e instanceof Error && e.message === 'UNAUTHORIZED') {
        setError('Email này không được cấp quyền truy cập HAPURA HQ.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center scanline">
      <div className="text-center space-y-8 p-8">
        <div className="flex items-center justify-center gap-3">
          <Crosshair size={32} className="text-brand text-glow-brand" />
          <h1 className="font-game text-4xl font-bold text-brand text-glow-brand tracking-widest">
            HAPURA HQ
          </h1>
        </div>
        <p className="text-slate-500 font-mono text-sm tracking-widest">
          REVENUE WAR ROOM — AUTHORIZED ACCESS ONLY
        </p>
        <div className="h-px bg-gradient-to-r from-transparent via-brand/30 to-transparent" />
        {error && (
          <div className="flex items-center gap-2 bg-neon-red/10 border border-neon-red/30 rounded-lg px-4 py-3 text-neon-red text-sm font-mono">
            <ShieldAlert size={14} className="shrink-0" />
            {error}
          </div>
        )}
        <button
          onClick={handleLogin}
          disabled={loading}
          className="px-8 py-3 bg-brand/10 border border-brand/30 rounded-lg text-brand font-game font-bold tracking-widest hover:bg-brand/20 hover:glow-brand transition-all disabled:opacity-50"
        >
          {loading ? 'AUTHENTICATING...' : 'ACCESS WITH GOOGLE'}
        </button>
      </div>
    </div>
  )
}
