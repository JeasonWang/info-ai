import { get, post, put, del } from './request'
import type {
  Category,
  Channel,
  EventCategory,
  EventDetail,
  EventPage,
  FavoriteEventItem,
  InfoItem,
  InfoPage,
  ListEventParams,
  ListInfoParams,
  PublicUser,
  ReadHistoryItem,
  StatsData,
} from '@/types'

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
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
}

function normalizeEventListItem(item: EventPage['items'][number]) {
  return {
    ...item,
    source_badges: normalizeStringList(item.source_badges),
  }
}

export function getCategories() {
  return get<Category[]>('/categories')
}

export function getEventCategories() {
  return get<EventCategory[]>('/event-categories')
}

export function getChannels(categoryId?: number) {
  const query = categoryId ? `?category_id=${categoryId}` : ''
  return get<Channel[]>(`/channels${query}`)
}

export function getInfos(params: ListInfoParams) {
  const q = new URLSearchParams()
  if (params.category_id) q.set('category_id', String(params.category_id))
  if (params.channel_id) q.set('channel_id', String(params.channel_id))
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.page) q.set('page', String(params.page))
  if (params.page_size) q.set('page_size', String(params.page_size))
  const query = q.toString() ? `?${q.toString()}` : ''
  return get<InfoPage>(`/infos${query}`).then((res) => ({
    ...res,
    items: res.items.map(normalizeInfoItem),
  }))
}

export function getEvents(params: ListEventParams) {
  const q = new URLSearchParams()
  q.set('category_code', params.category_code ?? 'all')
  if (params.channel_code && params.channel_code !== 'all') q.set('channel_code', params.channel_code)
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.sort) q.set('sort', params.sort)
  if (params.page) q.set('page', String(params.page))
  if (params.page_size) q.set('page_size', String(params.page_size))
  return get<EventPage>(`/events?${q.toString()}`).then((res) => ({
    ...res,
    items: res.items.map(normalizeEventListItem),
  }))
}

export function getEventById(id: number) {
  return get<EventDetail>(`/events/${id}`)
}

export function getInfoById(id: number) {
  return get<InfoItem>(`/infos/${id}`).then(normalizeInfoItem)
}

export function getStats() {
  return get<StatsData>('/stats')
}

export function registerUser(email: string, password: string) {
  return post<PublicUser>('/auth/register', { email, password }, true)
}

export function loginUser(email: string, password: string) {
  return post<{ token: string; user: PublicUser }>('/auth/login', { email, password }, true)
}

export function getCurrentUser() {
  return get<PublicUser>('/me')
}

export function logoutUser() {
  return post<{ revoked: boolean }>('/auth/logout')
}

export function getFavoriteEventIds() {
  return get<{ event_ids: number[] }>('/me/favorites')
}

export function getFavoriteEvents() {
  return get<FavoriteEventItem[]>('/me/favorite-events')
}

export function addFavoriteEvent(eventId: number) {
  return post<{ event_id: number; favorited: boolean }>('/me/favorites', { event_id: eventId })
}

export function removeFavoriteEvent(eventId: number) {
  return del<{ event_id: number; favorited: boolean }>(`/me/favorites/${eventId}`)
}

interface HomeFilterPreferenceResponse {
  category_code: string
  channel_code?: string
  sort: 'composite' | 'latest'
  keyword: string
}

export function getHomeFilterPreference() {
  return get<HomeFilterPreferenceResponse>('/me/preferences/home-filter')
}

export function saveHomeFilterPreference(preference: {
  categoryCode: string
  channelCode: string
  sortMode: 'composite' | 'latest'
  keyword: string
}) {
  return put<HomeFilterPreferenceResponse>('/me/preferences/home-filter', {
    category_code: preference.categoryCode,
    channel_code: preference.channelCode,
    sort: preference.sortMode,
    keyword: preference.keyword,
  })
}

export function getReadHistory() {
  return get<ReadHistoryItem[]>('/me/read-history')
}

export function recordReadHistory(payload: { eventId?: number; infoId?: number }) {
  return post<{ recorded: boolean }>('/me/read-history', {
    event_id: payload.eventId,
    info_id: payload.infoId,
  })
}
