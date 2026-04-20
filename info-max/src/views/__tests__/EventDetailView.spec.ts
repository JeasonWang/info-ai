import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import EventDetailView from '@/views/EventDetailView.vue'

describe('EventDetailView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads event detail data and renders timeline, summaries and source links', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.includes('/api/events/9')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              event: {
                id: 9,
                title: '全网关注的热点事件',
                one_line_summary: '一句话看懂这个热点事件。',
                primary_category: { code: 'tech', name: '科技' },
                heat_score: 92,
                last_updated_at: '2026-04-19 12:00:00',
              },
              timeline: [
                {
                  id: 1,
                  occurred_at: '2026-04-19 09:00:00',
                  summary: '官方首次通报事件进展',
                  confidence: 0.98,
                },
              ],
              summaries: {
                what_happened: '这是发生了什么的摘要。',
                why_it_matters: '这件事为什么重要。',
                latest_update: '最新进展已经出现。',
              },
              source_views: [
                {
                  channel_name: '微博',
                  summary: '微博上出现了大量讨论。',
                },
              ],
              representative_sources: [
                {
                  info_id: 11,
                  title: '路透原始报道',
                  channel_name: '路透',
                  source_url: 'https://example.com/reuters',
                  event_time: '2026-04-19 12:00:00',
                },
              ],
            },
          }),
        )
      }

      return new Response('not found', { status: 404 })
    })

    vi.stubGlobal('fetch', fetchMock)

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/events/:id',
          component: EventDetailView,
        },
      ],
    })

    router.push('/events/9')
    await router.isReady()

    const wrapper = mount(EventDetailView, {
      global: {
        plugins: [router],
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/events/9'), expect.any(Object))
    expect(wrapper.text()).toContain('全网关注的热点事件')
    expect(wrapper.text()).toContain('重点结论')
    expect(wrapper.text()).toContain('最新进展')
    expect(wrapper.text()).toContain('为什么重要')
    expect(wrapper.text()).toContain('官方首次通报事件进展')
    expect(wrapper.text()).toContain('这件事为什么重要。')
    expect(wrapper.text()).toContain('微博上出现了大量讨论。')
    expect(wrapper.get('a[href="https://example.com/reuters"]').text()).toContain('路透原始报道')
  })

  it('uses router back when clicking the back button', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.includes('/api/events/9')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              event: {
                id: 9,
                title: '全网关注的热点事件',
                one_line_summary: '一句话看懂这个热点事件。',
                primary_category: { code: 'tech', name: '科技' },
                heat_score: 92,
                last_updated_at: '2026-04-19 12:00:00',
              },
              timeline: [],
              summaries: {
                what_happened: '这是发生了什么的摘要。',
                why_it_matters: '这件事为什么重要。',
                latest_update: '最新进展已经出现。',
              },
              source_views: [],
              representative_sources: [],
            },
          }),
        )
      }

      return new Response('not found', { status: 404 })
    })

    vi.stubGlobal('fetch', fetchMock)

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div>home</div>' } },
        { path: '/events/:id', component: EventDetailView },
      ],
    })

    router.push('/')
    await router.isReady()
    router.push('/events/9')
    await flushPromises()

    const wrapper = mount(EventDetailView, {
      global: {
        plugins: [router],
      },
    })

    await flushPromises()
    await wrapper.get('[data-testid="back-button"]').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/')
  })
})
