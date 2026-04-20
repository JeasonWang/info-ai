import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import InfoDetailView from '@/views/InfoDetailView.vue'

describe('InfoDetailView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uses router back when clicking the back button', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.includes('/api/infos/7')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              id: 7,
              title: '原始热点详情',
              content: '这里是热点详情正文。',
              category_id: 1,
              category_name: '热点事件',
              channel_id: 1,
              channel_name: '微博',
              source_id: 'wb-7',
              source_url: 'https://example.com/source',
              event_time: '2026-04-20 10:00:00',
              core_entity: '热点事件',
              location: '',
              indicator_name: '',
              indicator_value: '',
              detail_fetch_status: 'complete',
              detail_fetch_error: '',
              detail_strategy: 'topic_search',
              detail_score: 88,
              detail_content_length: 128,
              detail_fetched_at: '2026-04-20 10:05:00',
              created_at: '2026-04-20 10:05:00',
              updated_at: '2026-04-20 10:05:00',
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
        { path: '/info/:id', component: InfoDetailView },
      ],
    })

    router.push('/')
    await router.isReady()
    router.push('/info/7')
    await flushPromises()

    const wrapper = mount(InfoDetailView, {
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
