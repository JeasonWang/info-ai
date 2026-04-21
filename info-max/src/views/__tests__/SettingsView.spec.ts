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

      if (url.includes('/api/infos?page=1&page_size=20')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              total: 0,
              page: 1,
              page_size: 5,
              items: [],
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

      if (url.includes('/api/infos?page=1&page_size=20')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              total: 0,
              page: 1,
              page_size: 5,
              items: [],
            },
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

  it('shows acquisition quality records on the admin page', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.endsWith('/api/admin/categories')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: [{ id: 1, name: '热点事件', code: 'hot', description: '热点资讯' }],
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
                name: '微博',
                code: 'weibo',
                base_url: 'https://weibo.com',
                category_id: 1,
                category_name: '热点事件',
                crawl_interval: 30,
                is_active: 1,
              },
            ],
          }),
        )
      }

      if (url.includes('/api/infos?page=1&page_size=20')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              total: 4,
              page: 1,
              page_size: 20,
              items: [
                {
                  id: 11,
                  title: '微博热点样例',
                  content: '抓取到的完整正文',
                  category_id: 1,
                  category_name: '热点事件',
                  channel_id: 1,
                  channel_name: '微博',
                  source_id: 'wb-11',
                  source_url: 'https://example.com/wb-11',
                  event_time: '2026-04-20 10:00:00',
                  core_entity: '微博热点',
                  location: '',
                  indicator_name: '',
                  indicator_value: '',
                  detail_fetch_status: 'complete',
                  detail_fetch_error: '',
                  detail_strategy: 'topic_search',
                  detail_score: 88,
                  detail_content_length: 226,
                  detail_fetched_at: '2026-04-20 10:05:00',
                  tech_topic_type: 'chip_release',
                  tech_entities: ['英伟达', 'H200'],
                  tech_keywords: ['显存', '训练效率'],
                  created_at: '2026-04-20 10:05:00',
                  updated_at: '2026-04-20 10:05:00',
                },
                {
                  id: 12,
                  title: '微博热点失败样例',
                  content: '抓取失败',
                  category_id: 1,
                  category_name: '热点事件',
                  channel_id: 1,
                  channel_name: '微博',
                  source_id: 'wb-12',
                  source_url: 'https://example.com/wb-12',
                  event_time: '2026-04-20 10:10:00',
                  core_entity: '微博热点',
                  location: '',
                  indicator_name: '',
                  indicator_value: '',
                  detail_fetch_status: 'failed',
                  detail_fetch_error: 'anti_crawl_blocked',
                  detail_strategy: 'topic_search',
                  detail_score: 0,
                  detail_content_length: 0,
                  detail_fetched_at: '2026-04-20 10:11:00',
                  created_at: '2026-04-20 10:11:00',
                  updated_at: '2026-04-20 10:11:00',
                },
                {
                  id: 13,
                  title: '微博热点部分详情样例',
                  content: '部分详情',
                  category_id: 1,
                  category_name: '热点事件',
                  channel_id: 1,
                  channel_name: '微博',
                  source_id: 'wb-13',
                  source_url: 'https://example.com/wb-13',
                  event_time: '2026-04-20 10:12:00',
                  core_entity: '微博热点',
                  location: '',
                  indicator_name: '',
                  indicator_value: '',
                  detail_fetch_status: 'partial',
                  detail_fetch_error: 'weak_relevance',
                  detail_strategy: 'mobile_search',
                  detail_score: 58,
                  detail_content_length: 61,
                  detail_fetched_at: '2026-04-20 10:13:00',
                  tech_topic_type: 'dev_tool',
                  tech_entities: ['MCP'],
                  tech_keywords: ['API', '开发工具'],
                  created_at: '2026-04-20 10:13:00',
                  updated_at: '2026-04-20 10:13:00',
                },
                {
                  id: 14,
                  title: '微博热点列表摘要样例',
                  content: '列表摘要',
                  category_id: 1,
                  category_name: '热点事件',
                  channel_id: 1,
                  channel_name: '微博',
                  source_id: 'wb-14',
                  source_url: 'https://example.com/wb-14',
                  event_time: '2026-04-20 10:14:00',
                  core_entity: '微博热点',
                  location: '',
                  indicator_name: '',
                  indicator_value: '',
                  detail_fetch_status: 'list_only',
                  detail_fetch_error: 'detail_unavailable',
                  detail_strategy: 'list_fallback',
                  detail_score: 10,
                  detail_content_length: 4,
                  detail_fetched_at: '2026-04-20 10:15:00',
                  created_at: '2026-04-20 10:15:00',
                  updated_at: '2026-04-20 10:15:00',
                },
                {
                  id: 15,
                  title: '微博热点第二条失败样例',
                  content: '抓取失败',
                  category_id: 1,
                  category_name: '热点事件',
                  channel_id: 1,
                  channel_name: '微博',
                  source_id: 'wb-15',
                  source_url: 'https://example.com/wb-15',
                  event_time: '2026-04-20 10:16:00',
                  core_entity: '微博热点',
                  location: '',
                  indicator_name: '',
                  indicator_value: '',
                  detail_fetch_status: 'failed',
                  detail_fetch_error: 'anti_crawl_blocked',
                  detail_strategy: 'web_fallback',
                  detail_score: 0,
                  detail_content_length: 0,
                  detail_fetched_at: '2026-04-20 10:17:00',
                  created_at: '2026-04-20 10:17:00',
                  updated_at: '2026-04-20 10:17:00',
                },
              ],
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

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/infos?page=1&page_size=20'),
      expect.any(Object),
    )
    expect(wrapper.text()).toContain('采集质量看板')
    expect(wrapper.text()).toContain('完整详情')
    expect(wrapper.text()).toContain('抓取失败')
    expect(wrapper.text()).toContain('部分详情')
    expect(wrapper.text()).toContain('仅列表摘要')
    expect(wrapper.text()).toContain('微博热点样例')
    expect(wrapper.text()).toContain('topic_search')
    expect(wrapper.text()).toContain('科技主题')
    expect(wrapper.text()).toContain('芯片发布')
    expect(wrapper.text()).toContain('关键词')
    expect(wrapper.text()).toContain('显存')
    expect(wrapper.text()).toContain('训练效率')
    expect(wrapper.text()).toContain('英伟达')
    expect(wrapper.text()).toContain('H200')
    expect(wrapper.text()).toContain('科技主题分布')
    expect(wrapper.text()).toContain('开发工具')
    expect(wrapper.text()).toContain('关键词热点')
    expect(wrapper.text()).toContain('API')
    expect(wrapper.text()).toContain('88')
    expect(wrapper.text()).toContain('226')
    expect(wrapper.get('[data-testid="quality-tech-diagnostics"]').text()).toContain('芯片发布')
    expect(wrapper.get('[data-testid="quality-tech-diagnostics"]').text()).toContain('显存')
    expect(wrapper.get('[data-testid="quality-tech-diagnostics"]').text()).toContain('训练效率')
    expect(wrapper.get('[data-testid="quality-tech-diagnostics"]').text()).toContain('英伟达')
    expect(wrapper.get('[data-testid="quality-tech-diagnostics"]').text()).toContain('H200')
    expect(wrapper.get('[data-testid="quality-summary-complete"]').text()).toContain('1')
    expect(wrapper.get('[data-testid="quality-summary-partial"]').text()).toContain('1')
    expect(wrapper.get('[data-testid="quality-summary-list_only"]').text()).toContain('1')
    expect(wrapper.get('[data-testid="quality-summary-failed"]').text()).toContain('2')
    expect(wrapper.get('[data-testid="quality-average-score"]').text()).toContain('31.2')
    expect(wrapper.get('[data-testid="quality-top-error"]').text()).toContain('anti_crawl_blocked')
    expect(wrapper.get('[data-testid="quality-top-error"]').text()).toContain('2 次')
    expect(wrapper.get('[data-testid="quality-top-strategy"]').text()).toContain('topic_search')
    expect(wrapper.get('[data-testid="quality-top-strategy"]').text()).toContain('2 条')
    expect(wrapper.get('[data-testid="quality-score-trend"]').text()).toContain('质量分趋势')
    expect(wrapper.get('[data-testid="quality-score-trend"]').text()).toContain('上升')
    expect(wrapper.get('[data-testid="quality-complete-trend"]').text()).toContain('完整率趋势')
    expect(wrapper.get('[data-testid="quality-failed-trend"]').text()).toContain('失败率趋势')
    expect(wrapper.get('[data-testid="quality-error-distribution"]').text()).toContain('anti_crawl_blocked')
    expect(wrapper.get('[data-testid="quality-error-distribution"]').text()).toContain('weak_relevance')
    expect(wrapper.get('[data-testid="quality-error-distribution"]').text()).toContain('detail_unavailable')
    expect(wrapper.get('[data-testid="quality-strategy-distribution"]').text()).toContain('topic_search')
    expect(wrapper.get('[data-testid="quality-strategy-distribution"]').text()).toContain('mobile_search')
    expect(wrapper.get('[data-testid="quality-strategy-distribution"]').text()).toContain('list_fallback')
    expect(wrapper.get('[data-testid="quality-channel-trends"]').text()).toContain('渠道趋势')
    expect(wrapper.get('[data-testid="quality-channel-trends"]').text()).toContain('微博')
    expect(wrapper.get('[data-testid="quality-channel-trends"]').text()).toContain('质量上升')
    expect(wrapper.get('[data-testid="quality-topic-distribution"]').text()).toContain('芯片发布')
    expect(wrapper.get('[data-testid="quality-topic-distribution"]').text()).toContain('开发工具')
    expect(wrapper.get('[data-testid="quality-keyword-distribution"]').text()).toContain('显存')
    expect(wrapper.get('[data-testid="quality-keyword-distribution"]').text()).toContain('API')
  })
})
