import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  getCategories,
  getChannels,
  getEventById,
  getEventCategories,
  getEvents,
  getInfoById,
  getInfos,
  getCurrentUser,
  getHomeFilterPreference,
  getFavoriteEvents,
  getReadHistory,
  getFavoriteEventIds,
  loginUser,
  logoutUser,
  recordReadHistory,
  registerUser,
  addFavoriteEvent,
  removeFavoriteEvent,
  saveHomeFilterPreference,
  getStats,
} from '@/services/api'

describe('api service routing', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uses info-serve /api/v1 for event APIs', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/event-categories')) {
        return jsonResponse([{ code: 'all', name: '全网', display_order: 0 }])
      }
      if (url.includes('/events/7')) {
        return jsonResponse({ event: { id: 7, title: '热点详情' }, timeline: [] })
      }
      return jsonResponse({ total: 0, page: 1, page_size: 10, items: [] })
    })
    vi.stubGlobal('fetch', fetchMock)

    await getEventCategories()
    await getEvents({ category_code: 'tech', sort: 'latest', page: 1, page_size: 10 })
    await getEventById(7)

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/event-categories',
      expect.any(Object),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/events?category_code=tech&sort=latest&page=1&page_size=10',
      expect.any(Object),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/events/7',
      expect.any(Object),
    )
  })

  it('normalizes nullable event source badges from info-serve', async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        total: 1,
        page: 1,
        page_size: 10,
        items: [
          {
            id: 7,
            representative_info_id: null,
            title: '热点事件',
            one_line_summary: '来源暂未识别',
            primary_category: { code: 'tech', name: '科技' },
            heat_score: 80,
            freshness_score: 70,
            composite_score: 90,
            last_updated_at: '2026-04-22 10:00:00',
            source_count: 1,
            source_badges: null,
            new_update_count: 0,
          },
        ],
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const page = await getEvents({ category_code: 'all', sort: 'composite', page: 1, page_size: 10 })

    expect(page.items[0].source_badges).toEqual([])
  })

  it('uses info-serve /api/v1 for remaining user-facing APIs', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/categories')) {
        return jsonResponse([{ id: 1, name: '科技', code: 'tech', description: '科技热点' }])
      }
      if (url.includes('/channels')) {
        return jsonResponse([{ id: 2, name: 'CSDN', code: 'csdn', category_id: 1 }])
      }
      if (url.includes('/infos/9')) {
        return jsonResponse({ id: 9, title: '原始资讯详情', tech_entities: 'OpenAI,MCP' })
      }
      if (url.includes('/infos?')) {
        return jsonResponse({ total: 1, page: 1, page_size: 10, items: [{ id: 9, title: '原始资讯详情' }] })
      }
      return jsonResponse({ total: 1, categories: [{ name: '科技', count: 1 }] })
    })
    vi.stubGlobal('fetch', fetchMock)

    await getCategories()
    await getChannels(1)
    await getInfos({ category_id: 1, channel_id: 2, keyword: 'OpenAI', page: 1, page_size: 10 })
    await getInfoById(9)
    await getStats()

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8080/api/v1/categories', expect.any(Object))
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8080/api/v1/channels?category_id=1', expect.any(Object))
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/infos?category_id=1&channel_id=2&keyword=OpenAI&page=1&page_size=10',
      expect.any(Object),
    )
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8080/api/v1/infos/9', expect.any(Object))
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8080/api/v1/stats', expect.any(Object))
  })

  it('uses /api/v1 auth APIs for user sessions', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/auth/login')) {
        return jsonResponse({ token: 'token', user: { id: 1, email: 'user@example.com', role: 'user', status: 'active' } })
      }
      if (url.includes('/auth/register')) {
        return jsonResponse({ id: 1, email: 'user@example.com', role: 'user', status: 'active' })
      }
      if (url.includes('/auth/logout')) {
        return jsonResponse({ revoked: true })
      }
      if (url.includes('/me/favorites') && init?.method === 'POST') {
        return jsonResponse({ event_id: 101, favorited: true })
      }
      if (url.includes('/me/favorites') && init?.method === 'DELETE') {
        return jsonResponse({ event_id: 101, favorited: false })
      }
      if (url.includes('/me/favorite-events')) {
        return jsonResponse([
          { id: 101, title: '收藏事件', one_line_summary: '收藏摘要', category_name: '科技', source_label: '微博', favorited_at: '2026-04-24 10:00:00', target_path: '/events/101' },
        ])
      }
      if (url.includes('/me/favorites')) {
        return jsonResponse({ event_ids: [101] })
      }
      if (url.includes('/me/preferences/home-filter') && init?.method === 'PUT') {
        return jsonResponse({ category_code: 'sports', sort: 'latest', keyword: 'NBA' })
      }
      if (url.includes('/me/preferences/home-filter')) {
        return jsonResponse({ category_code: 'sports', sort: 'latest', keyword: 'NBA' })
      }
      if (url.includes('/me/read-history') && init?.method === 'POST') {
        return jsonResponse({ recorded: true })
      }
      if (url.includes('/me/read-history')) {
        return jsonResponse([
          { item_type: 'event', event_id: 101, title: '最近阅读事件', subtitle: '科技', source_label: '微博', read_at: '2026-04-24 09:00:00', target_path: '/events/101', primary_remark: '摘要' },
        ])
      }
      return jsonResponse({ id: 1, email: 'user@example.com', role: 'user', status: 'active' })
    })
    vi.stubGlobal('fetch', fetchMock)

    await registerUser('user@example.com', 'StrongerPass123')
    await loginUser('user@example.com', 'StrongerPass123')
    await getCurrentUser('token')
    await getFavoriteEventIds('token')
    await getFavoriteEvents('token')
    await addFavoriteEvent('token', 101)
    await removeFavoriteEvent('token', 101)
    await getHomeFilterPreference('token')
    await saveHomeFilterPreference('token', { categoryCode: 'sports', channelCode: 'all', sortMode: 'latest', keyword: 'NBA' })
    await getReadHistory('token')
    await recordReadHistory('token', { eventId: 101 })
    await logoutUser('token')

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/auth/register',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/auth/login',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/me',
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer token' }) }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/me/favorites',
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer token' }) }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/me/favorite-events',
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer token' }) }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/me/favorites',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ event_id: 101 }) }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/me/favorites/101',
      expect.objectContaining({ method: 'DELETE' }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/me/preferences/home-filter',
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer token' }) }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/me/preferences/home-filter',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ category_code: 'sports', channel_code: 'all', sort: 'latest', keyword: 'NBA' }),
      }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/me/read-history',
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer token' }) }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/me/read-history',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ event_id: 101 }) }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/auth/logout',
      expect.objectContaining({ method: 'POST', headers: expect.objectContaining({ Authorization: 'Bearer token' }) }),
    )
  })
})

function jsonResponse(data: unknown) {
  return new Response(JSON.stringify({ code: 0, message: 'success', data }))
}
