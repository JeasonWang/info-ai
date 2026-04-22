import type {
  ApiResponse,
  Category,
  Channel,
  EventDetail,
  EventCategory,
  EventPage,
  InfoItem,
  InfoPage,
  ListEventParams,
  ListInfoParams,
  StatsData,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function buildQuery(params: Record<string, string | number | undefined | null>) {
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== null) {
      query.set(key, String(value))
    }
  })

  const queryString = query.toString()
  return queryString ? `?${queryString}` : ''
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<T>
}

function normalizeTechKeywords(value: unknown) {
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
  }

  if (typeof value === 'string') {
    return value
      .split(/[、,]/)
      .map((item) => item.trim())
      .filter(Boolean)
  }

  return undefined
}

function normalizeInfoItem(info: InfoItem): InfoItem {
  return {
    ...info,
    tech_topic_type: info.tech_topic_type?.trim() || undefined,
    tech_entities: normalizeTechKeywords(info.tech_entities),
    tech_keywords: normalizeTechKeywords(info.tech_keywords),
  }
}

export async function getCategories() {
  const response = await request<ApiResponse<Category[]>>('/api/categories')
  return response.data
}

export async function getEventCategories() {
  const response = await request<ApiResponse<EventCategory[]>>('/api/event-categories')
  return response.data
}

export async function getChannels(categoryId?: number) {
  const query = buildQuery({ category_id: categoryId })
  const response = await request<ApiResponse<Channel[]>>(`/api/channels${query}`)
  return response.data
}

export async function getInfos(params: ListInfoParams) {
  const query = buildQuery({
    category_id: params.category_id,
    channel_id: params.channel_id,
    keyword: params.keyword,
    page: params.page,
    page_size: params.page_size,
  })
  const response = await request<ApiResponse<InfoPage>>(`/api/infos${query}`)
  return {
    ...response.data,
    items: response.data.items.map(normalizeInfoItem),
  }
}

export async function getEvents(params: ListEventParams) {
  const query = buildQuery({
    category_code: params.category_code ?? 'all',
    keyword: params.keyword,
    sort: params.sort,
    page: params.page,
    page_size: params.page_size,
  })
  const response = await request<ApiResponse<EventPage>>(`/api/events${query}`)
  return response.data
}

export async function getEventById(id: number) {
  const response = await request<ApiResponse<EventDetail>>(`/api/events/${id}`)
  return response.data
}

export async function getInfoById(id: number) {
  const response = await request<ApiResponse<InfoItem>>(`/api/infos/${id}`)
  return normalizeInfoItem(response.data)
}

export async function getStats() {
  const response = await request<ApiResponse<StatsData>>('/api/stats')
  return response.data
}
