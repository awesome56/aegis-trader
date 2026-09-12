import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'

/**
 * TanStack Query setup.
 *
 * Defaults are tuned for a realtime terminal: short staleness for live data,
 * a single retry, and no refetch on window focus (the WebSocket keeps data
 * fresh). The realtime → cache bridge is registered once in `useRealtime()`.
 */
export default defineNuxtPlugin((nuxtApp) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 15_000,
        gcTime: 5 * 60_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  })

  nuxtApp.vueApp.use(VueQueryPlugin, { queryClient })

  return {
    provide: { queryClient },
  }
})
