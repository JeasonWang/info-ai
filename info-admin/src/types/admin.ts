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
  latest_info_at: string
  latest_event_at: string
  info_count: number
  active_event_count: number
  average_content_length: number
  incomplete_info_count: number
  top_failure_reasons: string[]
}

export interface ChannelQualityFailureReason {
  reason: string
  count: number
}

export interface ChannelQualityStrategy {
  strategy: string
  count: number
}

export interface ChannelQualityCredentialStatus {
  name: string
  configured: boolean
  source: string
  required: boolean
  length: number
  preview: string
  health: string
}

export interface ChannelQualityCredentialHealth {
  channel_code?: string
  health: string
  missing_required?: string[]
  credentials?: ChannelQualityCredentialStatus[]
}

export interface ChannelQualityWeakSample {
  id: number
  title: string
  source_url: string
  detail_fetch_status: string
  detail_strategy: string
  detail_score: number
  detail_content_length: number
  detail_fetch_error: string
  quality_level?: string
  completeness_score?: number
  value_score?: number
  required_length?: number
  attention_priority?: number
  risk_reasons?: string[]
  recommended_action?: string
  quality_summary?: string
}

export interface ChannelQualityWeakChannel {
  channel_code: string
  channel_name: string
  usable_ratio: number
  needs_attention_ratio: number
}

export interface ChannelQualitySummary {
  real_count: number
  complete_count: number
  high_value_partial_count: number
  usable_count: number
  needs_attention_count: number
  complete_ratio: number
  usable_ratio: number
  needs_attention_ratio: number
  weak_channels: ChannelQualityWeakChannel[]
}

export interface ChannelQualityItem {
  channel_id: number
  channel_code: string
  channel_name: string
  total_count: number
  real_count: number
  seed_count: number
  complete_count: number
  complete_ratio: number
  high_value_partial_count: number
  usable_count: number
  usable_ratio: number
  needs_attention_count: number
  needs_attention_ratio: number
  quality_rank_score: number
  governance_advice: string[]
  avg_detail_score: number
  avg_detail_content_length: number
  top_failure_reasons: ChannelQualityFailureReason[]
  top_detail_strategies: ChannelQualityStrategy[]
  credential_health: ChannelQualityCredentialHealth
  weak_samples: ChannelQualityWeakSample[]
}

export interface ChannelQualityReport {
  summary: ChannelQualitySummary
  channels: ChannelQualityItem[]
}

export interface EventAnalysisQualitySummary {
  active_event_count: number
  analyzed_count: number
  missing_analysis_count: number
  low_confidence_count: number
  fallback_count: number
  weak_source_event_count: number
  avg_confidence: number
  avg_quality_score: number
  risk_event_count: number
}

export interface EventAnalysisRiskEvent {
  event_id: number
  title: string
  one_line_summary: string
  source_count: number
  weak_source_count: number
  issue_reasons: string[]
  governance_advice: string[]
  risk_score: number
  run_id: number | null
  mode: string
  provider: string
  model_name: string
  status: string
  quality_score: number
  confidence: number
  fallback_used: boolean
  failure_reason: string
  last_analyzed_at: string
}

export interface EventAnalysisQualityReport {
  summary: EventAnalysisQualitySummary
  risk_events: EventAnalysisRiskEvent[]
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
  seed_detail_count: number
  real_detail_total: number
  real_complete_detail_count: number
  real_complete_detail_ratio: number
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

export interface RetryLowQualitySelectedSample {
  info_id: number
  title: string
  channel_code: string
  attention_priority: number
  quality_level: string
  risk_reasons: string[]
  recommended_action: string
  quality_summary: string
}

export interface RetryLowQualityActionData {
  selected_count?: number
  selected_samples?: RetryLowQualitySelectedSample[]
  detail_success_count?: number
  detail_failed_count?: number
}

export interface DetailJobFailureReason {
  reason: string
  count: number
}

export interface DetailJobSample {
  id: number
  info_id: number
  title: string
  channel_code: string
  status: string
  priority: number
  strategy_hint: string
  attempt_count: number
  max_attempts: number
  last_failure_reason: string
  next_run_at: string
  detail_score: number
  detail_fetch_status: string
}

export interface DetailJobReport {
  total: number
  status_counts: Record<string, number>
  channel_counts: Record<string, number>
  strategy_counts: Record<string, number>
  top_failure_reasons: DetailJobFailureReason[]
  pending_samples: DetailJobSample[]
  failed_samples: DetailJobSample[]
}

export interface DetailJobDetail extends DetailJobSample {
  source_url: string
  content: string
  detail_strategy: string
  created_at: string
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
  base_interval_minutes: number
  hot_interval_minutes: number
  min_interval_minutes: number
  max_interval_minutes: number
  manual_interval_enabled: number
  effective_interval_minutes: number
  schedule_version: number
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
  base_interval_minutes: number
  hot_interval_minutes: number
  min_interval_minutes: number
  max_interval_minutes: number
  manual_interval_enabled: number
  effective_interval_minutes: number
  is_active: number
}

export interface LLMModelConfig {
  id: number
  provider_name: string
  provider_code: string
  base_url: string
  api_key: string
  model_name: string
  is_enabled: number
  daily_call_limit: number
  daily_call_count: number
  last_call_date: string
  priority: number
  consecutive_failure_count: number
  circuit_open_until: string
  last_failure_reason: string
  success_count: number
  failure_count: number
  avg_latency_ms: number
  last_error_message: string
  created_at: string
  updated_at: string
}

export interface LLMModelConfigPayload {
  provider_name: string
  provider_code: string
  base_url: string
  api_key: string
  model_name: string
  is_enabled: number
  daily_call_limit: number
  daily_call_count: number
  priority: number
}

export interface LLMChatTestPayload {
  config_id?: number
  prompt: string
  timeout_seconds: number
}

export interface LLMChatTestResult {
  ok: boolean
  status: string
  config_id?: number
  provider_code?: string
  model_name?: string
  latency_ms?: number
  status_code?: number
  content?: string
  json?: Record<string, unknown> | null
  usage?: Record<string, unknown>
  message?: string
}

export interface LLMChatPayload {
  config_id?: number
  message: string
  timeout_seconds: number
}

export interface LLMChatResult {
  ok: boolean
  status: string
  answer?: string
  content?: string
  config_id?: number
  provider_code?: string
  model_name?: string
  latency_ms?: number
  status_code?: number
  usage?: Record<string, unknown>
  message?: string
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
  data: RetryLowQualityActionData & Record<string, unknown>
}
