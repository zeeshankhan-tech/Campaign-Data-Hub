/** Minimal typed API client for Campaign Data Hub backend. */

import type {
  DeliveriesQuery,
  DeliveryListResponse,
  HealthResponse,
  MetricsQuery,
  MetricsResponse,
  QualityReportResponse,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init)
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) {
        detail = body.detail
      }
    } catch {
      // keep status-based message
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

function toQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      search.set(key, String(value))
    }
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/v1/health')
}

export async function fetchMetrics(query: MetricsQuery = {}): Promise<MetricsResponse> {
  return request<MetricsResponse>(
    `/api/v1/metrics${toQuery({
      platform: query.platform,
      date_from: query.date_from,
      date_to: query.date_to,
      group_by: query.group_by ?? 'campaign',
      limit: query.limit ?? 100,
      offset: query.offset ?? 0,
    })}`,
  )
}

export async function fetchDeliveries(
  query: DeliveriesQuery = {},
): Promise<DeliveryListResponse> {
  return request<DeliveryListResponse>(
    `/api/v1/deliveries${toQuery({
      platform: query.platform,
      health: query.health,
      limit: query.limit ?? 100,
      offset: query.offset ?? 0,
    })}`,
  )
}

export async function fetchQualityReport(
  deliveryId: string,
): Promise<QualityReportResponse> {
  return request<QualityReportResponse>(`/api/v1/deliveries/${deliveryId}/quality-report`)
}
