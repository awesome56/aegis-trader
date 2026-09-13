import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AuditTimeline from '~/components/AuditTimeline.vue'

describe('AuditTimeline', () => {
  it('renders only the stages provided', () => {
    const wrapper = mount(AuditTimeline, {
      props: {
        stages: [
          { key: 'created', label: 'Proposal created', status: 'done', at: '2026-01-15 15:00:00' },
          { key: 'order', label: 'Broker order', status: 'pending' },
        ],
      },
    })
    const text = wrapper.text()
    expect(text).toContain('Proposal created')
    expect(text).toContain('Broker order')
    expect(text).not.toContain('Execution / fill')
  })

  it('renders a failed stage detail', () => {
    const wrapper = mount(AuditTimeline, {
      props: {
        stages: [
          { key: 'decision', label: 'Risk approved / rejected', status: 'failed', detail: 'Exposure limit exceeded' },
        ],
      },
    })
    expect(wrapper.text()).toContain('Exposure limit exceeded')
  })
})
