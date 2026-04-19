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
  detail_fetch_status: 'pending' | 'success' | 'failed' | string
  detail_fetch_error: string
  created_at: string | null
  updated_at: string | null
}

export interface InfoPage {
  total: number
  page: number
  page_size: number
  items: InfoItem[]
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
