import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import EventList from '@/components/EventList.vue'

describe('EventList', () => {
  it('renders event cards with summary, sources and detail link', () => {
    const wrapper = mount(EventList, {
      props: {
        items: [
          {
            id: 7,
            representative_info_id: 27,
            title: 'OpenAI 新模型能力引发全网讨论',
            one_line_summary: '一句话先看懂这件事发生了什么。',
            primary_category: { code: 'tech', name: '科技' },
            heat_score: 95,
            freshness_score: 88,
            composite_score: 92,
            last_updated_at: '2026-04-19 12:30:00',
            source_count: 4,
            source_badges: ['微博', '36氪', '路透'],
            new_update_count: 3,
          },
        ],
        loading: false,
        total: 1,
        hasMore: false,
        loadingMore: false,
        loadMoreError: '',
      },
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    expect(wrapper.text()).toContain('OpenAI 新模型能力引发全网讨论')
    expect(wrapper.text()).toContain('一句话先看懂这件事发生了什么。')
    expect(wrapper.find('[data-testid="event-card-signal"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-testid="event-card-stat"]')).toHaveLength(0)
    expect(wrapper.text()).toContain('热度 95')
    expect(wrapper.text()).toContain('4 来源')
    expect(wrapper.text()).toContain('新增 3')
    expect(wrapper.text()).toContain('微博')
    expect(wrapper.text()).not.toContain('36氪')
    expect(wrapper.text()).not.toContain('进展')
    expect(wrapper.find('[data-testid="event-card-meta"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="event-card-meta"]').text()).toContain('科技')
    expect(wrapper.find('[data-testid="event-card-meta"]').text()).toContain('微博')
    expect(wrapper.find('[data-testid="event-card-meta"]').text()).toContain('2026-04-19 12:30:00')
    expect(wrapper.findAll('.event-card__actions .button')).toHaveLength(1)
    const links = wrapper.findAllComponents(RouterLinkStub)
    expect(links).toHaveLength(3)
    expect(links[0].props('to')).toBe('/info/27')
    expect(links[1].props('to')).toBe('/info/27')
    expect(links[2].props('to')).toBe('/events/7')
    expect(wrapper.text()).toContain('时间线')
    expect(wrapper.text()).toContain('查看详情')
    expect(wrapper.text()).toContain('已经看完本频道')
    expect(wrapper.text()).not.toContain('上一页')
    expect(wrapper.text()).not.toContain('下一页')
    expect(wrapper.text()).not.toContain('第 1 /')
  })

  it('shows a lightweight loading-more state', () => {
    const wrapper = mount(EventList, {
      props: {
        items: [
          {
            id: 7,
            representative_info_id: 27,
            title: 'OpenAI 新模型能力引发全网讨论',
            one_line_summary: '一句话先看懂这件事发生了什么。',
            primary_category: { code: 'tech', name: '科技' },
            heat_score: 95,
            freshness_score: 88,
            composite_score: 92,
            last_updated_at: '2026-04-19 12:30:00',
            source_count: 4,
            source_badges: ['微博'],
            new_update_count: 3,
          },
        ],
        loading: false,
        total: 2,
        hasMore: true,
        loadingMore: true,
        loadMoreError: '',
      },
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    expect(wrapper.get('[data-testid="infinite-status"]').text()).toContain('正在加载更多热点')
  })

  it('renders an empty state and emits retry', async () => {
    const wrapper = mount(EventList, {
      props: {
        items: [],
        loading: false,
        total: 0,
        hasMore: false,
        loadingMore: false,
        loadMoreError: '',
      },
    })

    expect(wrapper.text()).toContain('当前还没有可展示的热点事件')

    await wrapper.get('button').trigger('click')

    expect(wrapper.emitted('retry')).toEqual([[]])
  })
})
