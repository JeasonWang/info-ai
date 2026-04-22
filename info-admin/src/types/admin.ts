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
