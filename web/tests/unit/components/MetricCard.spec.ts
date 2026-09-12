import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import MetricCard from '~/components/ui/MetricCard.vue'

describe('MetricCard', () => {
  it('renders the label and value', () => {
    const wrapper = mount(MetricCard, {
      props: { label: 'Portfolio Value', value: '$127,480.25', delta: '+1.47%' },
    })
    expect(wrapper.text()).toContain('Portfolio Value')
    expect(wrapper.text()).toContain('$127,480.25')
    expect(wrapper.text()).toContain('+1.47%')
  })

  it('renders a placeholder dash when no value is provided', () => {
    const wrapper = mount(MetricCard, { props: { label: 'Buying Power' } })
    expect(wrapper.text()).toContain('—')
  })

  it('shows a skeleton instead of a value while loading', () => {
    const wrapper = mount(MetricCard, {
      props: { label: 'Equity', value: '$1.00', loading: true },
    })
    expect(wrapper.find('.animate-pulse').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('$1.00')
  })
})
