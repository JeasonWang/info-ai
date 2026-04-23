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
  LoginResult,
  PublicUser,
  StatsData,
} from '@/types'

const INFO_SERVE_BASE_URL = import.meta.env.VITE_INFO_SERVE_BASE_URL || 'http://localhost:8080'
const INFO_SERVE_API_PREFIX = '/api/v1'

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

async function requestInfoServe<T>(path: string, init?: RequestInit): Promise<T> {
  return requestFromBase<T>(INFO_SERVE_BASE_URL, `${INFO_SERVE_API_PREFIX}${path}`, init)
}

async function requestFromBase<T>(baseURL: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseURL}${path}`, {
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

function normalizeStringList(value: unknown) {
  if (!Array.isArray(value)) {
    return []
  }

  return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
}

function normalizeEventListItem(item: EventPage['items'][number]) {
  return {
    ...item,
    source_badges: normalizeStringList(item.source_badges),
  }
}

export async function getCategories() {
  const response = await requestInfoServe<ApiResponse<Category[]>>('/categories')
  return response.data
}

export async function getEventCategories() {
  const response = await requestInfoServe<ApiResponse<EventCategory[]>>('/event-categories')
  return response.data
}

export async function getChannels(categoryId?: number) {
	const query = buildQuery({ category_id: categoryId })
  const response = await requestInfoServe<ApiResponse<Channel[]>>(`/channels${query}`)
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
  const response = await requestInfoServe<ApiResponse<InfoPage>>(`/infos${query}`)
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
  const response = await requestInfoServe<ApiResponse<EventPage>>(`/events${query}`)
  return {
    ...response.data,
    items: response.data.items.map(normalizeEventListItem),
  }
}

export async function getEventById(id: number) {
  const response = await requestInfoServe<ApiResponse<EventDetail>>(`/events/${id}`)
  return response.data
}

export async function getInfoById(id: number) {
  const response = await requestInfoServe<ApiResponse<InfoItem>>(`/infos/${id}`)
  return normalizeInfoItem(response.data)
}

export async function getStats() {
  const response = await requestInfoServe<ApiResponse<StatsData>>('/stats')
  return response.data
}

export async function registerUser(email: string, password: string) {
  const response = await requestInfoServe<ApiResponse<PublicUser>>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  return response.data
}

export async function loginUser(email: string, password: string) {
  const response = await requestInfoServe<ApiResponse<LoginResult>>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  return response.data
}

export async function getCurrentUser(token: string) {
  const response = await requestInfoServe<ApiResponse<PublicUser>>('/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}

export async function logoutUser(token: string) {
  const response = await requestInfoServe<ApiResponse<{ revoked: boolean }>>('/auth/logout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}
