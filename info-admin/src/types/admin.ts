export interface QualityOverview {
  duplicate_title_count: number
  empty_content_count: number
  low_detail_score_count: number
  missing_entity_count: number
}

export interface CrawlRunSummary {
  channel_code: string
  status: string
  raw_count: number
  cleaned_count: number
  saved_count: number
  detail_success_count: number
  detail_failed_count: number
  started_at: string
  finished_at: string
}

export interface ChannelHealth {
  channel_code: string
  channel_name: string
  category_name: string
  status: string
  recent_run_count: number
  success_rate: number
  detail_complete_rate: number
  health_score: number
  health_level: 'healthy' | 'warning' | 'risk'
  failure_count: number
  last_run_at: string
  last_issue: string
}

export interface AdminOverview {
  channel_count: number
  event_count: number
  info_count: number
  quality: QualityOverview
  recent_runs: CrawlRunSummary[]
}

export interface QualitySnapshot {
  category_code: string
  total_count: number
  duplicate_title_count: number
  empty_content_count: number
  low_detail_score_count: number
  missing_entity_count: number
  snapshot_at: string
}

export interface LowQualityInfo {
  id: number
  title: string
  channel_name: string
  category_name: string
  detail_fetch_status: string
  detail_score: number
  detail_content_length: number
  issue_reason: string
  updated_at: string
}

export interface CrawlTask {
  task_code: string
  task_name: string
  channel_code: string
  channel_name: string
  schedule_type: string
  schedule_value: string
  status: string
  last_run_at: string
  next_run_at: string
}

export interface AdminCategory {
  id: number
  name: string
  code: string
  description: string
  created_at: string
  updated_at: string
}

export interface CategoryPayload {
  name: string
  code: string
  description: string
}

export interface AdminChannel {
  id: number
  name: string
  code: string
  base_url: string
  category_id: number
  category_name: string
  crawl_interval: number
  is_active: number
  created_at: string
  updated_at: string
}

export interface ChannelPayload {
  name: string
  code: string
  base_url: string
  category_id: number
  crawl_interval: number
  is_active: number
}

export interface AuditLog {
  id: number
  admin_user_id: number
  admin_email: string
  action: string
  target_type: string
  target_id: string
  ip_address: string
  created_at: string
}

export interface AdminActionResult {
  action: string
  message: string
  data: Record<string, unknown>
}
