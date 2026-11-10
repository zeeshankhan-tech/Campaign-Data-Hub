/** Backend API response types used by the dashboard. */

export type HealthResponse = {
  status: string
  app: string
  environment: string
  database: string
}

export type PaginationMeta = {
  limit: number
  offset: number
  total: number
}

export type MetricTotals = {
  spend_usd: string
  impressions: number
  clicks: number
  ctr: string | null
  cpc: string | null
}

export type MetricGroupItem = {
  platform?: string | null
  campaign?: string | null
  spend_usd: string
  impressions: number
  clicks: number
  ctr: string | null
  cpc: string | null
}

export type MetricsResponse = {
  group_by: 'campaign' | 'platform'
  items: MetricGroupItem[]
  totals: MetricTotals
  pagination: PaginationMeta
}

export type DeliveryItem = {
  id: string
  platform: string
  week_start: string
  source_filename: string | null
  content_checksum: string | null
  health: string
  ingested_at: string
  last_run_id: string | null
}

export type DeliveryListResponse = {
  items: DeliveryItem[]
  pagination: PaginationMeta
}

export type QualityFindingItem = {
  id: string
  check_id: string
  severity: string
  outcome: string
  message: string
  affected_entities?: Record<string, unknown> | null
  details?: Record<string, unknown> | null
}

export type QualityReportResponse = {
  delivery: DeliveryItem
  findings: QualityFindingItem[]
}

export type MetricsQuery = {
  platform?: string
  date_from?: string
  date_to?: string
  group_by?: 'campaign' | 'platform'
  limit?: number
  offset?: number
}

export type DeliveriesQuery = {
  platform?: string
  health?: string
  limit?: number
  offset?: number
}
