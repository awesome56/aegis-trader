import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SignalEvidenceTable from '~/components/SignalEvidenceTable.vue'

describe('SignalEvidenceTable', () => {
  it('renders readable indicator rows', () => {
    const wrapper = mount(SignalEvidenceTable, {
      props: { indicators: { rsi: 61.4, macd: 1.18, signal: 0.93, relative_volume: 1.42 } },
    })
    const text = wrapper.text()
    expect(text).toContain('rsi')
    expect(text).toContain('61.40')
    expect(text).toContain('macd')
    expect(text).toContain('1.18')
    expect(text).toContain('relative volume')
    expect(text).toContain('1.42')
  })

  it('shows an empty state when no structured evidence is returned', () => {
    const wrapper = mount(SignalEvidenceTable, { props: { indicators: null } })
    expect(wrapper.text()).toContain('No structured evidence')
  })
})
