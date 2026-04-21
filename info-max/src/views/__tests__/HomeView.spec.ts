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

      if (url.includes('/api/events?category_code=all&keyword=OpenAI')) {
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
                id: 3,
                representative_info_id: 13,
                title: 'OpenAI 搜索结果',
                  one_line_summary: '搜索后命中的事件摘要。',
                  primary_category: { code: 'all', name: '全网' },
                  heat_score: 92,
                  freshness_score: 84,
                  composite_score: 89,
                  last_updated_at: '2026-04-20 10:00:00',
                  source_count: 2,
                  source_badges: ['36氪', '微博'],
                  new_update_count: 1,
                },
              ],
            },
          }),
        )
      }

      if (url.includes('/api/events?category_code=tech&keyword=OpenAI')) {
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
                  id: 4,
                  representative_info_id: 14,
                  title: '科技频道 OpenAI 热点',
                  one_line_summary: '在科技频道中继续保留关键词筛选。',
                  primary_category: { code: 'tech', name: '科技' },
                  heat_score: 94,
                  freshness_score: 86,
                  composite_score: 91,
                  last_updated_at: '2026-04-20 11:00:00',
                  source_count: 3,
                  source_badges: ['36氪', '知乎'],
                  new_update_count: 2,
                },
              ],
            },
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
                  representative_info_id: 12,
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
                representative_info_id: 11,
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
    vi.stubGlobal('scrollTo', vi.fn())

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
    expect(wrapper.find('[data-testid="home-compact-header"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="home-channel-strip"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('热点事件')
    expect(wrapper.text()).toContain('全网 · 1 条')
    expect(wrapper.text()).not.toContain('一句话刷懂全网热点')
    expect(wrapper.text()).not.toContain('当前频道')
    expect(wrapper.text()).not.toContain('事件数量')
    expect(wrapper.text()).toContain('全网综合热点')
    expect(wrapper.text()).not.toContain('管理配置')

    await wrapper.get('[data-code="tech"]').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/events?category_code=tech&page=1&page_size=10'),
      expect.any(Object),
    )
    expect(wrapper.text()).toContain('科技频道热点')

    await wrapper.get('input[type="search"]').setValue('OpenAI')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/events?category_code=tech&keyword=OpenAI&page=1&page_size=10'),
      expect.any(Object),
    )
    expect(wrapper.text()).toContain('科技频道 OpenAI 热点')
  })

  it('shows a back-to-top button after scrolling and scrolls smoothly to the top', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.endsWith('/api/event-categories')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: [{ code: 'all', name: '全网', display_order: 0 }],
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
            items: [],
          },
        }),
      )
    })
    const scrollTo = vi.fn()
    Object.defineProperty(window, 'scrollY', { value: 520, writable: true })
    vi.stubGlobal('fetch', fetchMock)
    vi.stubGlobal('scrollTo', scrollTo)

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    await flushPromises()
    window.dispatchEvent(new Event('scroll'))
    await wrapper.vm.$nextTick()

    const button = wrapper.get('[data-testid="back-to-top"]')
    await button.trigger('click')

    expect(scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' })
  })

  it('automatically appends the next page when the bottom sentinel enters the viewport', async () => {
    let intersectionCallback: IntersectionObserverCallback | null = null
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.endsWith('/api/event-categories')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: [{ code: 'all', name: '全网', display_order: 0 }],
          }),
        )
      }

      if (url.includes('page=2')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              total: 3,
              page: 2,
              page_size: 2,
              items: [
                {
                  id: 3,
                  representative_info_id: 33,
                  title: '第三条自动加载热点',
                  one_line_summary: '这是自动加载出来的新热点。',
                  primary_category: { code: 'all', name: '全网' },
                  heat_score: 82,
                  freshness_score: 76,
                  composite_score: 80,
                  last_updated_at: '2026-04-19 13:00:00',
                  source_count: 1,
                  source_badges: ['36氪'],
                  new_update_count: 0,
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
            total: 3,
            page: 1,
            page_size: 2,
            items: [
              {
                id: 1,
                representative_info_id: 31,
                title: '第一条首页热点',
                one_line_summary: '第一页的第一条热点。',
                primary_category: { code: 'all', name: '全网' },
                heat_score: 90,
                freshness_score: 85,
                composite_score: 88,
                last_updated_at: '2026-04-19 12:00:00',
                source_count: 2,
                source_badges: ['微博'],
                new_update_count: 1,
              },
              {
                id: 2,
                representative_info_id: 32,
                title: '第二条首页热点',
                one_line_summary: '第一页的第二条热点。',
                primary_category: { code: 'all', name: '全网' },
                heat_score: 88,
                freshness_score: 80,
                composite_score: 84,
                last_updated_at: '2026-04-19 12:30:00',
                source_count: 2,
                source_badges: ['知乎'],
                new_update_count: 1,
              },
            ],
          },
        }),
      )
    })

    vi.stubGlobal('fetch', fetchMock)
    vi.stubGlobal('scrollTo', vi.fn())
    vi.stubGlobal(
      'IntersectionObserver',
      vi.fn((callback: IntersectionObserverCallback) => {
        intersectionCallback = callback
        return {
          observe: vi.fn(),
          disconnect: vi.fn(),
          unobserve: vi.fn(),
          takeRecords: vi.fn(() => []),
        }
      }),
    )

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('第一条首页热点')
    expect(wrapper.text()).toContain('第二条首页热点')

    expect(intersectionCallback).toBeTruthy()
    const triggerIntersection = intersectionCallback as unknown as IntersectionObserverCallback
    triggerIntersection([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver)
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/events?category_code=all&page=2&page_size=10'),
      expect.any(Object),
    )
    expect(wrapper.text()).toContain('第一条首页热点')
    expect(wrapper.text()).toContain('第三条自动加载热点')
    expect(wrapper.text()).not.toContain('上一页')
    expect(wrapper.text()).not.toContain('下一页')
  })
})
