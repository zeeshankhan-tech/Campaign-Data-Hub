import { useEffect, useState } from 'react'
import { fetchDeliveries, fetchQualityReport } from '../api/client'
import type { DeliveryItem, DeliveryListResponse, QualityReportResponse } from '../api/types'
import { HealthBadge } from '../components/HealthBadge'
import { StatePanel } from '../components/StatePanel'

type ListState =
  | { status: 'loading' }
  | { status: 'ready'; data: DeliveryListResponse }
  | { status: 'error'; message: string }

type ReportState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; data: QualityReportResponse }
  | { status: 'error'; message: string }

const PLATFORMS = ['', 'meta', 'google', 'linkedin'] as const
const HEALTHS = ['', 'pass', 'warn', 'fail'] as const

export function DataHealthPage() {
  const [platform, setPlatform] = useState('')
  const [health, setHealth] = useState('')
  const [listState, setListState] = useState<ListState>({ status: 'loading' })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [reportState, setReportState] = useState<ReportState>({ status: 'idle' })

  useEffect(() => {
    let cancelled = false
    setListState({ status: 'loading' })
    setSelectedId(null)
    setReportState({ status: 'idle' })

    fetchDeliveries({
      platform: platform || undefined,
      health: health || undefined,
      limit: 100,
    })
      .then((data) => {
        if (!cancelled) setListState({ status: 'ready', data })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Failed to load deliveries'
          setListState({ status: 'error', message })
        }
      })

    return () => {
      cancelled = true
    }
  }, [platform, health])

  useEffect(() => {
    if (!selectedId) {
      setReportState({ status: 'idle' })
      return
    }

    let cancelled = false
    setReportState({ status: 'loading' })
    fetchQualityReport(selectedId)
      .then((data) => {
        if (!cancelled) setReportState({ status: 'ready', data })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Failed to load quality report'
          setReportState({ status: 'error', message })
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedId])

  function onSelect(delivery: DeliveryItem) {
    setSelectedId(delivery.id)
  }

  return (
    <section className="view">
      <header className="view-header">
        <h2>Data health</h2>
        <p>Delivery health classifications with drill-down into quality-check findings.</p>
      </header>

      <div className="filters">
        <label>
          Platform
          <select value={platform} onChange={(event) => setPlatform(event.target.value)}>
            {PLATFORMS.map((value) => (
              <option key={value || 'all'} value={value}>
                {value || 'All platforms'}
              </option>
            ))}
          </select>
        </label>
        <label>
          Health
          <select value={health} onChange={(event) => setHealth(event.target.value)}>
            {HEALTHS.map((value) => (
              <option key={value || 'all'} value={value}>
                {value || 'All statuses'}
              </option>
            ))}
          </select>
        </label>
      </div>

      {listState.status === 'loading' && <StatePanel status="loading" message="Loading deliveries…" />}
      {listState.status === 'error' && <StatePanel status="error" message={listState.message} />}
      {listState.status === 'ready' && listState.data.items.length === 0 && (
        <StatePanel status="empty" message="No deliveries match the current filters." />
      )}

      {listState.status === 'ready' && listState.data.items.length > 0 && (
        <div className="split">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Platform</th>
                  <th>Week start</th>
                  <th>Health</th>
                  <th>Source file</th>
                </tr>
              </thead>
              <tbody>
                {listState.data.items.map((delivery) => (
                  <tr
                    key={delivery.id}
                    className={selectedId === delivery.id ? 'selected' : undefined}
                    onClick={() => onSelect(delivery)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        onSelect(delivery)
                      }
                    }}
                    tabIndex={0}
                    role="button"
                    aria-label={`Open quality report for ${delivery.platform} ${delivery.week_start}`}
                  >
                    <td>{delivery.platform}</td>
                    <td>{delivery.week_start}</td>
                    <td>
                      <HealthBadge health={delivery.health} />
                    </td>
                    <td>{delivery.source_filename ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <aside className="detail-panel" aria-live="polite">
            <h3>Quality report</h3>
            {reportState.status === 'idle' && (
              <p className="muted">Select a delivery to inspect check outcomes.</p>
            )}
            {reportState.status === 'loading' && <StatePanel status="loading" message="Loading report…" />}
            {reportState.status === 'error' && <StatePanel status="error" message={reportState.message} />}
            {reportState.status === 'ready' && (
              <>
                <p>
                  <HealthBadge health={reportState.data.delivery.health} />{' '}
                  {reportState.data.delivery.platform} · {reportState.data.delivery.week_start}
                </p>
                {reportState.data.findings.length === 0 ? (
                  <StatePanel status="empty" message="No quality findings for this delivery." />
                ) : (
                  <ul className="finding-list">
                    {reportState.data.findings.map((finding) => (
                      <li key={finding.id} className={`finding finding-${finding.outcome}`}>
                        <div className="finding-head">
                          <strong>{finding.check_id}</strong>
                          <span>
                            {finding.severity}/{finding.outcome}
                          </span>
                        </div>
                        <p>{finding.message}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </aside>
        </div>
      )}
    </section>
  )
}
