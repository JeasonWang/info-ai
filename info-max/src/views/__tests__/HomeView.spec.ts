import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import HomeView from '@/views/HomeView.vue'

describe('HomeView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads event categories and the event feed, then refetches after selecting another category', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.endsWith('/api/event-categories')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: [
              { code: 'all', name: '全网', display_order: 0 },
              { code: 'tech', name: '科技', display_order: 1 },
            ],
          }),
        )
      }

      if (url.includes('/api/events?category_code=tech')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              total: 1,
              page: 1,
              page_size: 10,
              items: [
                {
                  id: 2,
                  title: '科技频道热点',
                  one_line_summary: '这是科技频道的一句话摘要。',
                  primary_category: { code: 'tech', name: '科技' },
                  heat_score: 80,
                  freshness_score: 75,
                  composite_score: 78,
                  last_updated_at: '2026-04-19 13:00:00',
                  source_count: 2,
                  source_badges: ['36氪', '微博'],
                  new_update_count: 1,
                },
              ],
            },
          }),
        )
      }

      return new Response(
        JSON.stringify({
          code: 0,
          message: 'success',
          data: {
            total: 1,
            page: 1,
            page_size: 10,
            items: [
              {
                id: 1,
                title: '全网综合热点',
                one_line_summary: '这是首页的第一条热点摘要。',
                primary_category: { code: 'all', name: '全网' },
                heat_score: 90,
                freshness_score: 85,
                composite_score: 88,
                last_updated_at: '2026-04-19 12:00:00',
                source_count: 3,
                source_badges: ['微博', '路透'],
                new_update_count: 2,
              },
            ],
          },
        }),
      )
    })

    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/event-categories'),
      expect.any(Object),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/events?category_code=all&page=1&page_size=10'),
      expect.any(Object),
    )
    expect(wrapper.text()).toContain('全网综合热点')

    await wrapper.get('[data-code="tech"]').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/events?category_code=tech&page=1&page_size=10'),
      expect.any(Object),
    )
    expect(wrapper.text()).toContain('科技频道热点')
  })
})
