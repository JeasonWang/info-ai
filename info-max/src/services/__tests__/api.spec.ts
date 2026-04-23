import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  getCategories,
  getChannels,
  getEventById,
  getEventCategories,
  getEvents,
  getInfoById,
  getInfos,
  getStats,
} from '@/services/api'

describe('api service routing', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uses info-serve /api/v1 for event APIs', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
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

  it('uses info-serve /api/v1 for remaining user-facing APIs', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
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
})

function jsonResponse(data: unknown) {
  return new Response(JSON.stringify({ code: 0, message: 'success', data }))
}
