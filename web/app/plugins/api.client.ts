import { configureApi } from '~/services/api/config'
import { setRefreshToken } from '~/services/api/token'

/**
 * Copy Nuxt public runtime config into the framework-agnostic API config module,
 * and hydrate the persisted refresh token so the client can mint an access
 * token on startup. Runs before any store or query is used.
 */
export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()

  configureApi({
    baseUrl: config.public.apiBaseUrl,
    wsUrl: config.public.wsBaseUrl,
    useMock: config.public.useMockApi,
    appName: config.public.appName,
    appVersion: config.public.appVersion,
  })

  const refreshCookie = useCookie<string | null>('aegis.refresh_token')
  if (refreshCookie.value) setRefreshToken(refreshCookie.value)
})
