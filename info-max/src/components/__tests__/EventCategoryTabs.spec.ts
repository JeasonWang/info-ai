import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import EventCategoryTabs from '@/components/EventCategoryTabs.vue'

describe('EventCategoryTabs', () => {
  it('renders categories and emits the selected code', async () => {
    const wrapper = mount(EventCategoryTabs, {
      props: {
        categories: [
          { code: 'all', name: '全网', display_order: 0 },
          { code: 'tech', name: '科技', display_order: 1 },
          { code: 'economy', name: '财经', display_order: 2 },
        ],
        activeCode: 'all',
      },
    })

    expect(wrapper.text()).toContain('全网')
    expect(wrapper.text()).toContain('科技')
    expect(wrapper.get('[data-code="all"]').classes()).toContain('event-tab--active')

    await wrapper.get('[data-code="tech"]').trigger('click')

    expect(wrapper.emitted('select')).toEqual([['tech']])
  })
})
