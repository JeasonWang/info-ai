import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import FavoriteEventsView from '@/views/FavoriteEventsView.vue'

describe('FavoriteEventsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('renders signed-in favorite event items', async () => {
    localStorage.setItem('info-max-token', 'session-token')

    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/v1/me/favorite-events')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: [
              {
                id: 9,
                title: '收藏的热点事件',
                one_line_summary: '这是收藏事件摘要。',
                category_name: '科技',
                source_label: '微博',
                favorited_at: '2026-04-24 10:00:00',
                target_path: '/events/9',
              },
            ],
          }),
        )
      }
      return new Response('not found', { status: 404 })
    })

    vi.stubGlobal('fetch', fetchMock)

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/favorites', component: FavoriteEventsView }],
    })

    router.push('/favorites')
    await router.isReady()

    const wrapper = mount(FavoriteEventsView, {
      global: {
        plugins: [router],
        stubs: { RouterLink: RouterLinkStub },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('我的收藏')
    expect(wrapper.text()).toContain('收藏的热点事件')
    expect(wrapper.text()).toContain('这是收藏事件摘要')
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/me/favorite-events'),
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer session-token' }) }),
    )
  })
})
