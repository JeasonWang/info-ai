import { afterEach, describe, expect, it, vi } from 'vitest'
import { getEventById, getEventCategories, getEvents, getInfoById } from '@/services/api'

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

  it('keeps legacy FastAPI path for info detail before Go API is ready', async () => {
    const fetchMock = vi.fn(async () => {
      return jsonResponse({ id: 9, title: '原始资讯详情' })
    })
    vi.stubGlobal('fetch', fetchMock)

    await getInfoById(9)

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/infos/9', expect.any(Object))
  })
})

function jsonResponse(data: unknown) {
  return new Response(JSON.stringify({ code: 0, message: 'success', data }))
}
