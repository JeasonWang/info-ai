export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PublicUser {
  id: number
  email: string
  role: string
  status: string
}

export interface LoginResult {
  token: string
  user: PublicUser
}

export interface Category {
  id: number
  name: string
  code: string
  description: string
  created_at?: string | null
  updated_at?: string | null
}

export interface Channel {
  id: number
  name: string
  code: string
  base_url: string
  category_id: number
  category_name?: string
  crawl_interval: number
  is_active: number
  created_at?: string | null
  updated_at?: string | null
}

export interface InfoItem {
  id: number
  title: string
  content: string
  category_id: number
  category_name: string
  channel_id: number
  channel_name: string
  source_id: string
  source_url: string
  event_time: string | null
  core_entity: string
  location: string
  indicator_name: string
  indicator_value: string
  detail_fetch_status: 'pending' | 'list_only' | 'partial' | 'complete' | 'failed' | string
  detail_fetch_error: string
  detail_strategy: string
  detail_score: number
  detail_content_length: number
  detail_fetched_at: string | null
  quality_level?: string
  quality_summary?: string
  needs_attention?: boolean
  attention_priority?: number
  tech_topic_type?: string | null
  tech_entities?: string[] | null
  tech_keywords?: string[] | null
  created_at: string | null
  updated_at: string | null
}

export interface InfoPage {
  total: number
  page: number
  page_size: number
  items: InfoItem[]
}

export interface EventCategory {
  code: string
  name: string
  display_order: number
}

export interface EventListItem {
  id: number
  representative_info_id: number | null
  status?: 'active' | 'monitoring' | string
  title: string
  one_line_summary: string
  primary_category: {
    code: string
    name: string
  }
  heat_score: number
  freshness_score: number
  composite_score: number
  display_quality_score?: number
  display_quality_level?: string
  display_quality_reason?: string
  last_updated_at: string | null
  source_count: number
  source_badges: string[]
  new_update_count: number
}

export interface EventPage {
  total: number
  page: number
  page_size: number
  items: EventListItem[]
}

export interface EventTimelineItem {
  id: number
  occurred_at: string
  summary: string
  confidence: number
}

export interface EventSourceView {
  channel_name: string
  summary: string
  focus?: string
  stance?: string
  difference_hint?: string
}

export interface EventEvidenceSource {
  info_id: number
  title: string
  channel_name: string
  source_url: string
  weight: number
  detail_score: number
  detail_fetch_status: string
  quality_level: string
  quality_summary: string
  risk_reasons: string[]
}

export interface EventPlatformView {
  channel_name: string
  source_count: number
}

export interface EventEvidenceChain {
  evidence_sources: EventEvidenceSource[]
  weak_sources: EventEvidenceSource[]
  platform_views: EventPlatformView[]
  usable_source_count: number
  weak_source_count: number
}

export interface EventRepresentativeSource {
  info_id: number
  title: string
  channel_name: string
  source_url: string
  event_time: string | null
  content: string
  detail_fetch_status: string
  detail_score: number
  detail_content_length: number
  quality_level?: string
  quality_summary?: string
}

export interface EventTechTopic {
  topic_type: string
  count: number
}

export interface EventTechContext {
  topics: EventTechTopic[]
  entities: string[]
  keywords: string[]
}

export interface EventIntelligenceBrief {
  stage: string
  confidence_reason: string
  decision_hint: string
  follow_up_questions: string[]
}

export interface EventControversyBrief {
  level: 'none' | 'low' | 'medium' | 'high' | string
  title: string
  summary: string
  signals: string[]
  action_hint: string
  has_rumor_signal: boolean
}

export interface EventRelatedEvent {
  id: number
  title: string
  one_line_summary: string
  last_updated_at: string | null
  relation_type: 'previous' | 'next' | string
  relation_label: string
  relation_reason: string
  evolution_type: string
  evolution_summary: string
}

export interface EventDetail {
  event: {
    id: number
    status?: 'active' | 'monitoring' | string
    title: string
    one_line_summary: string
    primary_category: {
      code: string
      name: string
    }
    heat_score: number
    freshness_score?: number
    composite_score?: number
    display_quality_score?: number
    display_quality_level?: string
    display_quality_reason?: string
    source_count?: number
    last_updated_at: string | null
  }
  timeline: EventTimelineItem[]
  summaries: Record<string, string>
  source_views: EventSourceView[]
  representative_sources: EventRepresentativeSource[]
  tech_context: EventTechContext
  evidence_chain?: EventEvidenceChain
  intelligence_brief?: EventIntelligenceBrief
  controversy_brief?: EventControversyBrief
  related_events?: EventRelatedEvent[]
}

export interface StatsData {
  total: number
  categories: Array<{
    name: string
    count: number
  }>
}

export interface ReadHistoryItem {
  item_type: 'event' | 'info'
  event_id?: number | null
  info_id?: number | null
  title: string
  subtitle: string
  source_label: string
  read_at: string
  target_path: string
  primary_remark: string
}

export interface FavoriteEventItem {
  id: number
  title: string
  one_line_summary: string
  category_name: string
  source_label: string
  favorited_at: string
  target_path: string
}

export interface ListInfoParams {
  category_id?: number
  channel_id?: number
  keyword?: string
  page?: number
  page_size?: number
}

export interface ListEventParams {
  category_code?: string
  channel_code?: string
  keyword?: string
  status?: 'active' | 'monitoring'
  sort?: 'composite' | 'latest'
  page?: number
  page_size?: number
}
