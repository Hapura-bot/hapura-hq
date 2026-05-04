import { Link, useLocation } from 'react-router-dom'
import { Crosshair, LogOut, Zap, Send } from 'lucide-react'
import { useAuthContext } from '../../AuthContext'

const NAV_LINKS = [
  { to: '/vertex-config', icon: Zap,  label: 'VERTEX' },
  { to: '/auto-social',   icon: Send, label: 'SOCIAL' },
]

export function CommandNav() {
  const { pathname } = useLocation()
  const { user, signOut } = useAuthContext()

  return (
    <nav className="sticky top-0 z-50 bg-dark-800/95 border-b border-dark-600 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-game text-xl font-bold text-brand tracking-widest text-glow-brand">
          <Crosshair size={18} />
          HAPURA<span className="text-slate-500 font-normal mx-1">·</span>HQ
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-1">
          {NAV_LINKS.map(({ to, icon: Icon, label }) => (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-game font-semibold tracking-wider transition-all ${
                (to === '/' ? pathname === '/' : pathname.startsWith(to))
                  ? 'bg-brand/15 text-brand border border-brand/30'
                  : 'text-slate-500 hover:text-slate-300 border border-transparent'
              }`}
            >
              <Icon size={13} />
              {label}
            </Link>
          ))}
        </div>

        {/* User */}
        <div className="flex items-center gap-3">
          {user && (
            <>
              <span className="text-xs text-slate-500 font-mono hidden md:block">
                {user.email?.split('@')[0]}
              </span>
              <button
                onClick={signOut}
                className="flex items-center gap-1 text-slate-600 hover:text-neon-red transition-colors"
              >
                <LogOut size={14} />
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
