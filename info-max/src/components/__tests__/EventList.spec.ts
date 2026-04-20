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
        page: 1,
        pageSize: 10,
      },
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    expect(wrapper.text()).toContain('OpenAI 新模型能力引发全网讨论')
    expect(wrapper.text()).toContain('一句话先看懂这件事发生了什么。')
    expect(wrapper.text()).toContain('一句话看懂')
    expect(wrapper.text()).toContain('来源')
    expect(wrapper.text()).toContain('微博')
    expect(wrapper.text()).toContain('36氪')
    expect(wrapper.text()).toContain('进展')
    expect(wrapper.text()).toContain('3 条')
    const links = wrapper.findAllComponents(RouterLinkStub)
    expect(links).toHaveLength(2)
    expect(links[0].props('to')).toBe('/events/7')
    expect(links[1].props('to')).toBe('/info/27')
    expect(wrapper.text()).toContain('查看时间线')
    expect(wrapper.text()).toContain('查看详情')
  })

  it('renders an empty state and emits retry', async () => {
    const wrapper = mount(EventList, {
      props: {
        items: [],
        loading: false,
        total: 0,
        page: 1,
        pageSize: 10,
      },
    })

    expect(wrapper.text()).toContain('当前还没有可展示的热点事件')

    await wrapper.get('button').trigger('click')

    expect(wrapper.emitted('retry')).toEqual([[]])
  })
})
