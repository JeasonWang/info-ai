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
              content: '这条消息的核心是平台热度正在升温，值得继续观察。\n这里是热点详情正文。',
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
              tech_topic_type: 'chip_release',
              tech_entities: ['英伟达', 'H200'],
              tech_keywords: ['显存', '训练效率'],
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

  it('only renders the approved compact facts on the detail hero', async () => {
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
              content: '这条消息的核心是平台热度正在升温，值得继续观察。\n这里是热点详情正文。',
              category_id: 1,
              category_name: '热点事件',
              channel_id: 1,
              channel_name: '微博',
              source_id: 'wb-7',
              source_url: 'https://example.com/source',
              event_time: '2026-04-20 10:00:00',
              core_entity: '热点事件',
              location: '北京',
              indicator_name: '热度',
              indicator_value: '88',
              detail_fetch_status: 'complete',
              detail_fetch_error: '',
              detail_strategy: 'topic_search',
              detail_score: 88,
              detail_content_length: 128,
              detail_fetched_at: '2026-04-20 10:05:00',
              tech_topic_type: 'chip_release',
              tech_entities: ['英伟达', 'H200'],
              tech_keywords: ['显存', '训练效率'],
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

    router.push('/info/7')
    await router.isReady()

    const wrapper = mount(InfoDetailView, {
      global: {
        plugins: [router],
      },
    })

    await flushPromises()

    expect(wrapper.find('[data-testid="info-detail-hero"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="info-acquisition-details"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="info-detail-diagnostics"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="info-detail-quickfacts"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="info-detail-summary-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="info-acquisition-summary"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="info-detail-tech-tags"]').exists()).toBe(false)
    const heroText = wrapper.get('[data-testid="info-detail-hero"]').text()
    expect(heroText).toContain('原始热点详情')
    expect(heroText).toContain('微博')
    expect(heroText).toContain('2026-04-20 10:00:00')
    expect(heroText).toContain('质量评分 88')
    expect(heroText).toContain('正文长度 128')
    expect(heroText).not.toContain('策略 topic_search')
    expect(heroText).not.toContain('完整详情')
    expect(heroText).not.toContain('北京')
    expect(heroText).not.toContain('英伟达')
    expect(heroText).not.toContain('H200')
    expect(heroText).not.toContain('2026-04-20 10:05:00')
    expect(wrapper.get('[data-testid="info-detail-meta-line"]').text()).toContain('热点事件 · 微博 · 2026-04-20 10:00:00')
    expect(wrapper.text()).not.toContain('采集说明')
    expect(wrapper.text()).not.toContain('科技主题')
    expect(wrapper.text()).not.toContain('芯片发布')
    expect(wrapper.text()).not.toContain('采集策略')
    expect(wrapper.text()).not.toContain('更新时间')
    expect(wrapper.get('[data-testid="detail-content"]').text()).not.toContain('这条消息的核心是平台热度正在升温')
  })

  it('hides tech diagnostics when semantic fields are empty', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.includes('/api/infos/7')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              id: 7,
              title: '普通热点详情',
              content: '这里是普通热点详情正文。',
              category_id: 1,
              category_name: '热点事件',
              channel_id: 1,
              channel_name: '微博',
              source_id: 'wb-7',
              source_url: 'https://example.com/source',
              event_time: '2026-04-20 10:00:00',
              core_entity: '普通热点',
              location: '',
              indicator_name: '',
              indicator_value: '',
              detail_fetch_status: 'complete',
              detail_fetch_error: '',
              detail_strategy: 'topic_search',
              detail_score: 88,
              detail_content_length: 128,
              detail_fetched_at: '2026-04-20 10:05:00',
              tech_topic_type: '',
              tech_entities: [],
              tech_keywords: [],
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
      routes: [{ path: '/info/:id', component: InfoDetailView }],
    })

    router.push('/info/7')
    await router.isReady()

    const wrapper = mount(InfoDetailView, {
      global: {
        plugins: [router],
      },
    })

    await flushPromises()

    expect(wrapper.find('[data-testid="info-detail-diagnostics"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="info-detail-tech-tags"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('未识别')
    expect(wrapper.text()).not.toContain('暂无')
  })

  it('deduplicates detail body and does not repeat raw content in the hero', async () => {
    const repeatedBody = [
      'OpenAI 发布新模型',
      'OpenAI 发布新模型后，开发者重点关注 API 接入节奏。',
      'OpenAI 发布新模型后，开发者重点关注 API 接入节奏。',
      '企业团队开始评估迁移成本和部署窗口。',
    ].join('\n')
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.includes('/api/infos/7')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              id: 7,
              title: 'OpenAI 发布新模型',
              content: repeatedBody,
              category_id: 1,
              category_name: '科技动向',
              channel_id: 1,
              channel_name: '36氪',
              source_id: 'tech-7',
              source_url: 'https://example.com/source',
              event_time: '2026-04-20 10:00:00',
              core_entity: 'OpenAI',
              location: '',
              indicator_name: '',
              indicator_value: '',
              detail_fetch_status: 'complete',
              detail_fetch_error: '',
              detail_strategy: 'topic_search',
              detail_score: 88,
              detail_content_length: 128,
              detail_fetched_at: '2026-04-20 10:05:00',
              tech_topic_type: '',
              tech_entities: [],
              tech_keywords: [],
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
      routes: [{ path: '/info/:id', component: InfoDetailView }],
    })

    router.push('/info/7')
    await router.isReady()

    const wrapper = mount(InfoDetailView, {
      global: {
        plugins: [router],
      },
    })

    await flushPromises()

    const heroText = wrapper.get('[data-testid="info-detail-hero"]').text()
    const contentText = wrapper.get('[data-testid="detail-content"]').text()
    expect(heroText).not.toContain('开发者重点关注 API 接入节奏')
    expect(contentText.match(/开发者重点关注 API 接入节奏/g)).toHaveLength(1)
    expect(contentText).not.toContain('OpenAI 发布新模型OpenAI 发布新模型')
    expect(contentText).toContain('企业团队开始评估迁移成本和部署窗口')
  })

  it('does not render a summary card when the first readable paragraph only repeats the title', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.includes('/api/infos/7')) {
        return new Response(
          JSON.stringify({
            code: 0,
            message: 'success',
            data: {
              id: 7,
              title: '国际金价突破2400美元',
              content: '国际金价突破2400美元\n受全球地缘政治风险推动，黄金配置需求升温。',
              category_id: 1,
              category_name: '经济数据',
              channel_id: 1,
              channel_name: '东方财富',
              source_id: 'em-7',
              source_url: 'https://example.com/source',
              event_time: '2026-04-20 10:00:00',
              core_entity: '国际金价',
              location: '',
              indicator_name: '',
              indicator_value: '',
              detail_fetch_status: 'complete',
              detail_fetch_error: '',
              detail_strategy: 'detail_page',
              detail_score: 92,
              detail_content_length: 96,
              detail_fetched_at: '2026-04-20 10:05:00',
              tech_topic_type: '',
              tech_entities: [],
              tech_keywords: [],
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
      routes: [{ path: '/info/:id', component: InfoDetailView }],
    })

    router.push('/info/7')
    await router.isReady()

    const wrapper = mount(InfoDetailView, {
      global: {
        plugins: [router],
      },
    })

    await flushPromises()

    expect(wrapper.find('[data-testid="info-detail-summary-card"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="detail-content"]').text()).toContain('受全球地缘政治风险推动')
  })
})
