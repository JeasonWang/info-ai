export interface ApiResponse<T> {
  code: number
  message: string
  data: T
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
  title: string
  one_line_summary: string
  primary_category: {
    code: string
    name: string
  }
  heat_score: number
  freshness_score: number
  composite_score: number
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
}

export interface EventRepresentativeSource {
  info_id: number
  title: string
  channel_name: string
  source_url: string
  event_time: string | null
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

export interface EventDetail {
  event: {
    id: number
    title: string
    one_line_summary: string
    primary_category: {
      code: string
      name: string
    }
    heat_score: number
    freshness_score?: number
    composite_score?: number
    source_count?: number
    last_updated_at: string | null
  }
  timeline: EventTimelineItem[]
  summaries: Record<string, string>
  source_views: EventSourceView[]
  representative_sources: EventRepresentativeSource[]
  tech_context: EventTechContext
}

export interface StatsData {
  total: number
  categories: Array<{
    name: string
    count: number
  }>
}

export interface CrawlTriggerResult {
  channel: string
  raw_count: number
  cleaned_count: number
  detail_fetched: number
}

export interface EventRebuildResult {
  event_count: number
}

export interface CategoryPayload {
  name: string
  code: string
  description: string
}

export interface ChannelPayload {
  name: string
  code: string
  base_url: string
  category_id: number
  crawl_interval: number
  is_active: number
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
  keyword?: string
  sort?: 'composite' | 'latest'
  page?: number
  page_size?: number
}
