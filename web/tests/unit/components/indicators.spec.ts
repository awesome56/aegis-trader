import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PnLValue from '~/components/ui/PnLValue.vue'
import PercentageValue from '~/components/ui/PercentageValue.vue'
import StatusBadge from '~/components/ui/StatusBadge.vue'

describe('PnLValue', () => {
  it('shows a signed gain with an up arrow', () => {
    const wrapper = mount(PnLValue, { props: { value: '1842.35' } })
    expect(wrapper.text()).toContain('+$1,842.35')
    expect(wrapper.text()).toContain('▲')
    expect(wrapper.classes()).toContain('text-up')
  })

  it('shows a loss with a down arrow', () => {
    const wrapper = mount(PnLValue, { props: { value: '-183.75' } })
    expect(wrapper.text()).toContain('-$183.75')
    expect(wrapper.text()).toContain('▼')
    expect(wrapper.classes()).toContain('text-down')
  })
})

describe('PercentageValue', () => {
  it('formats with an explicit sign', () => {
    const wrapper = mount(PercentageValue, { props: { value: '1.47', showSign: true } })
    expect(wrapper.text()).toBe('+1.47%')
  })

  it('colorizes gains when asked', () => {
    const wrapper = mount(PercentageValue, {
      props: { value: '-2.1', colorize: true },
    })
    expect(wrapper.classes()).toContain('text-down')
  })
})

describe('StatusBadge', () => {
  it('renders an uppercase label and tone class', () => {
    const wrapper = mount(StatusBadge, { props: { label: 'Paper Trading', tone: 'paper' } })
    expect(wrapper.text()).toContain('Paper Trading')
    expect(wrapper.classes().join(' ')).toContain('bg-paper/10')
  })

  it('renders a dot when requested', () => {
    const wrapper = mount(StatusBadge, { props: { label: 'Live', tone: 'live', dot: true } })
    expect(wrapper.find('span.bg-current').exists()).toBe(true)
  })
})
