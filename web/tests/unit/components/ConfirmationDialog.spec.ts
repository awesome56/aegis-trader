import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ConfirmationDialog from '~/components/ui/ConfirmationDialog.vue'

describe('ConfirmationDialog', () => {
  it('does not render when closed', () => {
    const wrapper = mount(ConfirmationDialog, { props: { open: false, title: 'Test' } })
    expect(wrapper.text()).not.toContain('Test')
  })

  it('renders title, description and consequences when open', () => {
    const wrapper = mount(ConfirmationDialog, {
      props: {
        open: true,
        title: 'Emergency stop',
        description: 'Halt all automated trading immediately.',
        consequences: ['No new orders', 'Pending orders cancelled'],
      },
    })
    const text = wrapper.text()
    expect(text).toContain('Emergency stop')
    expect(text).toContain('No new orders')
    expect(text).toContain('Pending orders cancelled')
  })

  it('requires the confirmation phrase before enabling confirm', async () => {
    const wrapper = mount(ConfirmationDialog, {
      props: {
        open: true,
        title: 'Emergency stop',
        tone: 'danger',
        confirmPhrase: 'EMERGENCY STOP',
      },
    })

    const confirmButton = () =>
      wrapper.findAll('button').find((button) => button.text().includes('Confirm'))

    expect(confirmButton()?.attributes('disabled')).toBeDefined()

    await wrapper.get('input').setValue('EMERGENCY STOP')
    expect(confirmButton()?.attributes('disabled')).toBeUndefined()

    await confirmButton()!.trigger('click')
    expect(wrapper.emitted('confirm')).toHaveLength(1)
  })

  it('emits cancel and update:open when dismissed', async () => {
    const wrapper = mount(ConfirmationDialog, { props: { open: true, title: 'Pause trading' } })
    // First button is the cancel button; click the overlay-free cancel control.
    const buttons = wrapper.findAll('button')
    await buttons[0]!.trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
    expect(wrapper.emitted('update:open')?.[0]).toEqual([false])
  })
})
