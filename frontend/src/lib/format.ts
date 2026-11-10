/** Display formatting helpers for metrics. */

export function formatSpend(value: string | null | undefined): string {
  if (value == null || value === '') return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return value
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num)
}

export function formatRatio(value: string | null | undefined): string {
  if (value == null) return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return value
  return num.toFixed(6)
}

export function formatPercent(value: string | null | undefined): string {
  if (value == null) return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return value
  return `${(num * 100).toFixed(2)}%`
}

export function formatInt(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('en-US').format(value)
}
