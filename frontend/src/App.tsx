import { useEffect, useState } from 'react'
import { fetchHealth } from './api/client'
import type { HealthResponse } from './api/types'
import { DataHealthPage } from './pages/DataHealthPage'
import { MetricsPage } from './pages/MetricsPage'
import './App.css'

type View = 'metrics' | 'health'

type BackendState =
  | { status: 'loading' }
  | { status: 'ready'; data: HealthResponse }
  | { status: 'error'; message: string }

function App() {
  const [view, setView] = useState<View>('metrics')
  const [backend, setBackend] = useState<BackendState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    fetchHealth()
      .then((data) => {
        if (!cancelled) setBackend({ status: 'ready', data })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Backend unavailable'
          setBackend({ status: 'error', message })
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Campaign Data Hub</p>
          <h1>Delivery analytics & data quality</h1>
        </div>
        <div className="backend-chip" aria-live="polite">
          {backend.status === 'loading' && 'Checking API…'}
          {backend.status === 'error' && `API offline: ${backend.message}`}
          {backend.status === 'ready' && (
            <>
              API {backend.data.status} · DB {backend.data.database}
            </>
          )}
        </div>
      </header>

      <nav className="tabs" aria-label="Primary">
        <button
          type="button"
          className={view === 'metrics' ? 'tab active' : 'tab'}
          onClick={() => setView('metrics')}
        >
          Campaign metrics
        </button>
        <button
          type="button"
          className={view === 'health' ? 'tab active' : 'tab'}
          onClick={() => setView('health')}
        >
          Data health
        </button>
      </nav>

      <main>{view === 'metrics' ? <MetricsPage /> : <DataHealthPage />}</main>
    </div>
  )
}

export default App
