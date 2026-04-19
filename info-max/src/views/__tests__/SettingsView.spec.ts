import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import SettingsView from '@/views/SettingsView.vue'

describe('SettingsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('triggers event rebuild from the admin page and shows the result count', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)

      if (url.endsWith('/api/admin/categories')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: [{ id: 1, name: '科技', code: 'tech', description: '科技资讯' }],
          }),
        )
      }

      if (url.endsWith('/api/admin/channels')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: [
              {
                id: 1,
                name: '36氪',
                code: '36kr',
                base_url: 'https://36kr.com',
                category_id: 1,
                category_name: '科技',
                crawl_interval: 30,
                is_active: 1,
              },
            ],
          }),
        )
      }

      if (url.endsWith('/api/admin/rebuild-events')) {
        expect(init?.method).toBe('POST')
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              event_count: 18,
            },
          }),
        )
      }

      return new Response('not found', { status: 404 })
    })

    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(SettingsView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    await flushPromises()

    await wrapper.get('[data-testid="rebuild-events"]').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/admin/rebuild-events'),
      expect.objectContaining({
        method: 'POST',
      }),
    )
    expect(wrapper.text()).toContain('事件已重建，共生成 18 个事件')
  })
})
