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
                what_happened: '这是发生了什么的摘要，当前讨论主要围绕 API、推理 展开。',
                why_it_matters: '这条事件已扩散到 2 个来源，讨论集中在 OpenAI 以及 API 等技术点，说明它正在形成跨平台的持续影响。',
                latest_update: '最新进展已经出现，当前新增讨论重点集中在 API、开发工具。',
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
              tech_context: {
                topics: [
                  { topic_type: 'model_release', count: 2 },
                  { topic_type: 'dev_tool', count: 1 },
                ],
                entities: ['OpenAI', 'MCP'],
                keywords: ['API', '推理', '开发工具'],
              },
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
    expect(wrapper.find('[data-testid="event-detail-hero"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="event-detail-meta"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="event-detail-core"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="event-detail-support"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="event-detail-quickfacts"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('全网关注的热点事件')
    expect(wrapper.text()).toContain('重点结论')
    expect(wrapper.text()).toContain('最新进展')
    expect(wrapper.text()).toContain('为什么重要')
    expect(wrapper.text()).toContain('技术上下文')
    expect(wrapper.text()).toContain('模型发布')
    expect(wrapper.get('[data-testid="event-detail-meta"]').text()).toContain('科技 · 2026-04-19 12:00:00 · 1 个来源')
    expect(wrapper.text()).not.toContain('时间线 1 条')
    expect(wrapper.text()).toContain('OpenAI')
    expect(wrapper.text()).toContain('MCP')
    expect(wrapper.text()).toContain('API')
    expect(wrapper.text()).toContain('推理')
    expect(wrapper.text()).toContain('开发工具')
    expect(wrapper.text()).toContain('当前讨论主要围绕 API、推理 展开')
    expect(wrapper.text()).toContain('跨平台的持续影响')
    expect(wrapper.text()).toContain('当前新增讨论重点集中在 API、开发工具')
    expect(wrapper.text()).toContain('官方首次通报事件进展')
    expect(wrapper.text()).not.toContain('多平台怎么说')
    expect(wrapper.text()).not.toContain('事件解读')
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
              tech_context: {
                topics: [],
                entities: [],
                keywords: [],
              },
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

  it('hides tech context when there is no useful tech metadata', async () => {
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
                title: '普通热点事件',
                one_line_summary: '普通热点事件摘要。',
                primary_category: { code: 'hot', name: '热点事件' },
                heat_score: 80,
                last_updated_at: '2026-04-19 12:00:00',
              },
              timeline: [],
              summaries: {
                what_happened: '普通热点事件摘要。',
                why_it_matters: '',
                latest_update: '',
              },
              source_views: [],
              representative_sources: [],
              tech_context: {
                topics: [],
                entities: [],
                keywords: [],
              },
            },
          }),
        )
      }

      return new Response('not found', { status: 404 })
    })

    vi.stubGlobal('fetch', fetchMock)

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/events/:id', component: EventDetailView }],
    })

    router.push('/events/9')
    await router.isReady()

    const wrapper = mount(EventDetailView, {
      global: {
        plugins: [router],
      },
    })

    await flushPromises()

    expect(wrapper.find('[data-testid="event-tech-context"]').exists()).toBe(false)
  })

  it('hides repeated hero summary and duplicate timeline entries', async () => {
    const repeatedSummary = 'OpenAI 发布新模型后，开发者重点关注 API 接入节奏。'
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
                title: 'OpenAI 发布新模型',
                one_line_summary: repeatedSummary,
                primary_category: { code: 'tech', name: '科技' },
                heat_score: 80,
                last_updated_at: '2026-04-19 12:00:00',
              },
              timeline: [
                {
                  id: 1,
                  occurred_at: '2026-04-19 09:00:00',
                  summary: repeatedSummary,
                  confidence: 0.98,
                },
              ],
              summaries: {
                what_happened: repeatedSummary,
                why_it_matters: '',
                latest_update: '',
              },
              source_views: [],
              representative_sources: [],
              tech_context: {
                topics: [],
                entities: [],
                keywords: [],
              },
            },
          }),
        )
      }

      return new Response('not found', { status: 404 })
    })

    vi.stubGlobal('fetch', fetchMock)

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/events/:id', component: EventDetailView }],
    })

    router.push('/events/9')
    await router.isReady()

    const wrapper = mount(EventDetailView, {
      global: {
        plugins: [router],
      },
    })

    await flushPromises()

    expect(wrapper.find('.detail-hero__summary').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('事件时间线')
  })
})
