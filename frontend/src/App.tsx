import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuthContext } from './AuthContext'
import { CommandNav } from './components/layout/CommandNav'
import ARIAChat from './components/aria/ARIAChat'
import DashboardPage from './pages/DashboardPage'
import RevenueBoardPage from './pages/RevenueBoardPage'
import AgentCouncilPage from './pages/AgentCouncilPage'
import SprintPage from './pages/SprintPage'
import LoginPage from './pages/LoginPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1 } },
})

function AppShell() {
  const { user, loading } = useAuthContext()

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-mono text-slate-600 tracking-widest">INITIALIZING...</span>
        </div>
      </div>
    )
  }

  if (!user) return <LoginPage />

  return (
    <div className="min-h-screen bg-dark-900 flex flex-col scanline">
      <CommandNav />
      <div className="flex-1">
        <Routes>
          <Route path="/"        element={<DashboardPage />} />
          <Route path="/revenue" element={<RevenueBoardPage />} />
          <Route path="/agents"  element={<AgentCouncilPage />} />
          <Route path="/sprint"  element={<SprintPage />} />
        </Routes>
      </div>
      <footer className="border-t border-dark-600 py-3 flex justify-center">
        <span className="text-xs font-mono text-slate-700 tracking-widest">HAPURA COMMAND CENTER v1.0</span>
      </footer>
      <ARIAChat />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AppShell />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  )
}
