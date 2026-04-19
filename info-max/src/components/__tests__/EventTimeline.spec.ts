import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import EventTimeline from '@/components/EventTimeline.vue'

describe('EventTimeline', () => {
  it('renders ordered timeline entries', () => {
    const wrapper = mount(EventTimeline, {
      props: {
        items: [
          {
            id: 1,
            occurred_at: '2026-04-19 09:00:00',
            summary: '官方首次发布说明',
            confidence: 0.96,
          },
          {
            id: 2,
            occurred_at: '2026-04-19 10:30:00',
            summary: '多家媒体跟进报道',
            confidence: 0.87,
          },
        ],
      },
    })

    expect(wrapper.findAll('.event-timeline__item')).toHaveLength(2)
    expect(wrapper.text()).toContain('官方首次发布说明')
    expect(wrapper.text()).toContain('2026-04-19 10:30:00')
  })
})
