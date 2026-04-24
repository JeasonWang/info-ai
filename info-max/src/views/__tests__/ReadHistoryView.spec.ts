import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ReadHistoryView from '@/views/ReadHistoryView.vue'

describe('ReadHistoryView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('renders signed-in read history items', async () => {
    localStorage.setItem('info-max-token', 'session-token')

    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/v1/me/read-history')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: [
              {
                item_type: 'event',
                event_id: 9,
                title: '最近读过的事件',
                subtitle: '科技',
                source_label: '微博',
                read_at: '2026-04-24 10:00:00',
                target_path: '/events/9',
                primary_remark: '事件摘要',
              },
              {
                item_type: 'info',
                info_id: 7,
                title: '最近读过的资讯',
                subtitle: '热点事件',
                source_label: '路透',
                read_at: '2026-04-24 09:30:00',
                target_path: '/info/7',
                primary_remark: '正文摘要',
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
      routes: [{ path: '/history', component: ReadHistoryView }],
    })

    router.push('/history')
    await router.isReady()

    const wrapper = mount(ReadHistoryView, {
      global: {
        plugins: [router],
        stubs: { RouterLink: RouterLinkStub },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('阅读历史')
    expect(wrapper.text()).toContain('最近读过的事件')
    expect(wrapper.text()).toContain('最近读过的资讯')
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/me/read-history'),
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer session-token' }) }),
    )
  })
})
