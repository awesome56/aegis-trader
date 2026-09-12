import { defineStore } from 'pinia'
import { useLocalStorage } from '@vueuse/core'

/** Transient UI/client preferences. No server data is duplicated here. */
export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = useLocalStorage('aegis.sidebar.collapsed', false)
  const mobileNavOpen = ref(false)
  const commandPaletteOpen = ref(false)

  function toggleSidebar(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setSidebarCollapsed(value: boolean): void {
    sidebarCollapsed.value = value
  }

  function toggleMobileNav(): void {
    mobileNavOpen.value = !mobileNavOpen.value
  }

  function closeMobileNav(): void {
    mobileNavOpen.value = false
  }

  function toggleCommandPalette(): void {
    commandPaletteOpen.value = !commandPaletteOpen.value
  }

  return {
    sidebarCollapsed,
    mobileNavOpen,
    commandPaletteOpen,
    toggleSidebar,
    setSidebarCollapsed,
    toggleMobileNav,
    closeMobileNav,
    toggleCommandPalette,
  }
})
