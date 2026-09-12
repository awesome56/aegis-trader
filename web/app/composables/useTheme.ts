export type ThemePreference = 'dark' | 'light' | 'system'

/**
 * Theme control (dark-first). Backed by `@nuxtjs/color-mode` (bundled with
 * Nuxt UI); the preference is persisted automatically.
 */
export function useTheme() {
  const colorMode = useColorMode()

  const preference = computed<ThemePreference>(
    () => (colorMode.preference as ThemePreference) ?? 'dark',
  )

  function setTheme(value: ThemePreference): void {
    colorMode.preference = value
  }

  function cycle(): void {
    const order: ThemePreference[] = ['dark', 'light', 'system']
    const index = order.indexOf(preference.value)
    const next = order[(index + 1) % order.length] ?? 'dark'
    setTheme(next)
  }

  return {
    preference,
    setTheme,
    cycle,
    options: ['dark', 'light', 'system'] as ThemePreference[],
  }
}
