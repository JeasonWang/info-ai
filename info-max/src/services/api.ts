import type {
  ApiResponse,
  Category,
  Channel,
  EventDetail,
  EventCategory,
  EventPage,
  FavoriteEventItem,
  InfoItem,
  InfoPage,
  ListEventParams,
  ListInfoParams,
  LoginResult,
  ReadHistoryItem,
  PublicUser,
  StatsData,
} from '@/types'
import type { HomeFilterMemory } from '@/services/homeFilterMemory'

const INFO_SERVE_BASE_URL = import.meta.env.VITE_INFO_SERVE_BASE_URL || 'http://localhost:8085'
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
    channel_code: params.channel_code && params.channel_code !== 'all' ? params.channel_code : undefined,
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

export async function getFavoriteEventIds(token: string) {
  const response = await requestInfoServe<ApiResponse<{ event_ids: number[] }>>('/me/favorites', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data.event_ids
}

export async function getFavoriteEvents(token: string): Promise<FavoriteEventItem[]> {
  const response = await requestInfoServe<ApiResponse<FavoriteEventItem[]>>('/me/favorite-events', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}

export async function addFavoriteEvent(token: string, eventId: number) {
  const response = await requestInfoServe<ApiResponse<{ event_id: number; favorited: boolean }>>('/me/favorites', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ event_id: eventId }),
  })
  return response.data
}

export async function removeFavoriteEvent(token: string, eventId: number) {
  const response = await requestInfoServe<ApiResponse<{ event_id: number; favorited: boolean }>>(`/me/favorites/${eventId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}

interface HomeFilterPreferenceResponse {
  category_code: string
  channel_code?: string
  sort: 'composite' | 'latest'
  keyword: string
}

function normalizeHomeFilterPreference(data: HomeFilterPreferenceResponse): HomeFilterMemory {
  return {
    categoryCode: data.category_code || 'all',
    channelCode: data.channel_code || 'all',
    sortMode: data.sort === 'latest' ? 'latest' : 'composite',
    keyword: data.keyword || '',
  }
}

export async function getHomeFilterPreference(token: string): Promise<HomeFilterMemory> {
  const response = await requestInfoServe<ApiResponse<HomeFilterPreferenceResponse>>('/me/preferences/home-filter', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return normalizeHomeFilterPreference(response.data)
}

export async function saveHomeFilterPreference(token: string, preference: HomeFilterMemory): Promise<HomeFilterMemory> {
  const response = await requestInfoServe<ApiResponse<HomeFilterPreferenceResponse>>('/me/preferences/home-filter', {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      category_code: preference.categoryCode,
      channel_code: preference.channelCode,
      sort: preference.sortMode,
      keyword: preference.keyword,
    }),
  })
  return normalizeHomeFilterPreference(response.data)
}

export async function getReadHistory(token: string): Promise<ReadHistoryItem[]> {
  const response = await requestInfoServe<ApiResponse<ReadHistoryItem[]>>('/me/read-history', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}

export async function recordReadHistory(token: string, payload: { eventId?: number; infoId?: number }) {
  const response = await requestInfoServe<ApiResponse<{ recorded: boolean }>>('/me/read-history', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      event_id: payload.eventId,
      info_id: payload.infoId,
    }),
  })
  return response.data
}
