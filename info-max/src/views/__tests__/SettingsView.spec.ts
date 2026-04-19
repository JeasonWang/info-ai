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

  it('triggers crawl for a channel from the admin page and shows the crawl summary', async () => {
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

      if (url.includes('/api/crawl/trigger?channel_code=36kr')) {
        expect(init?.method).toBe('POST')
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              channel: '36kr',
              raw_count: 16,
              cleaned_count: 9,
              detail_fetched: 6,
            },
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
              event_count: 21,
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

    await wrapper.get('[data-testid="trigger-crawl-36kr"]').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/crawl/trigger?channel_code=36kr'),
      expect.objectContaining({
        method: 'POST',
      }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/admin/rebuild-events'),
      expect.objectContaining({
        method: 'POST',
      }),
    )
    expect(wrapper.text()).toContain('36kr 抓取完成：原始 16 条，清洗后 9 条，详情补全 6 条；事件流已刷新，共生成 21 个事件')
  })
})
