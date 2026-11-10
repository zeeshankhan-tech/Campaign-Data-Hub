import { useEffect, useMemo, useState } from 'react'
import { fetchMetrics } from '../api/client'
import type { MetricGroupItem, MetricsResponse } from '../api/types'
import { StatePanel } from '../components/StatePanel'
import { formatInt, formatPercent, formatRatio, formatSpend } from '../lib/format'

type LoadState =
  | { status: 'loading' }
  | { status: 'ready'; data: MetricsResponse }
  | { status: 'error'; message: string }

type SortKey = 'spend' | 'ctr'
type SortDir = 'asc' | 'desc'

const PLATFORMS = ['', 'meta', 'google', 'linkedin'] as const

function compareNullableNumber(a: string | null | undefined, b: string | null | undefined): number {
  if (a == null && b == null) return 0
  if (a == null) return 1
  if (b == null) return -1
  return Number(a) - Number(b)
}

export function MetricsPage() {
  const [platform, setPlatform] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('spend')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })

    fetchMetrics({
      platform: platform || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      group_by: 'campaign',
      limit: 200,
    })
      .then((data) => {
        if (!cancelled) setState({ status: 'ready', data })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Failed to load metrics'
          setState({ status: 'error', message })
        }
      })

    return () => {
      cancelled = true
    }
  }, [platform, dateFrom, dateTo])

  const sortedItems = useMemo(() => {
    if (state.status !== 'ready') return [] as MetricGroupItem[]
    const items = [...state.data.items]
    items.sort((left, right) => {
      const raw =
        sortKey === 'spend'
          ? Number(left.spend_usd) - Number(right.spend_usd)
          : compareNullableNumber(left.ctr, right.ctr)
      return sortDir === 'asc' ? raw : -raw
    })
    return items
  }, [state, sortKey, sortDir])

  function toggleSort(next: SortKey) {
    if (sortKey === next) {
      setSortDir((dir) => (dir === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(next)
    setSortDir('desc')
  }

  return (
    <section className="view">
      <header className="view-header">
        <h2>Campaign metrics</h2>
        <p>Normalized spend, volume, CTR, and CPC from accepted delivery rows.</p>
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
          Date from
          <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        </label>
        <label>
          Date to
          <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        </label>
      </div>

      {state.status === 'loading' && <StatePanel status="loading" message="Loading metrics…" />}
      {state.status === 'error' && <StatePanel status="error" message={state.message} />}
      {state.status === 'ready' && state.data.items.length === 0 && (
        <StatePanel status="empty" message="No metrics match the current filters." />
      )}

      {state.status === 'ready' && state.data.items.length > 0 && (
        <>
          <div className="totals" aria-label="Totals for active filters">
            <div>
              <span>Spend</span>
              <strong>{formatSpend(state.data.totals.spend_usd)}</strong>
            </div>
            <div>
              <span>Impressions</span>
              <strong>{formatInt(state.data.totals.impressions)}</strong>
            </div>
            <div>
              <span>Clicks</span>
              <strong>{formatInt(state.data.totals.clicks)}</strong>
            </div>
            <div>
              <span>CTR</span>
              <strong>{formatPercent(state.data.totals.ctr)}</strong>
            </div>
            <div>
              <span>CPC</span>
              <strong>{formatSpend(state.data.totals.cpc)}</strong>
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Platform</th>
                  <th>Campaign</th>
                  <th>
                    <button type="button" className="sort-btn" onClick={() => toggleSort('spend')}>
                      Spend {sortKey === 'spend' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                    </button>
                  </th>
                  <th>Impressions</th>
                  <th>Clicks</th>
                  <th>
                    <button type="button" className="sort-btn" onClick={() => toggleSort('ctr')}>
                      CTR {sortKey === 'ctr' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                    </button>
                  </th>
                  <th>CPC</th>
                </tr>
              </thead>
              <tbody>
                {sortedItems.map((item) => (
                  <tr key={`${item.platform}-${item.campaign}`}>
                    <td>{item.platform}</td>
                    <td>{item.campaign}</td>
                    <td>{formatSpend(item.spend_usd)}</td>
                    <td>{formatInt(item.impressions)}</td>
                    <td>{formatInt(item.clicks)}</td>
                    <td title={formatRatio(item.ctr)}>{formatPercent(item.ctr)}</td>
                    <td>{formatSpend(item.cpc)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
