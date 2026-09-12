/**
 * Authentication guard.
 *
 * Applied globally (see auth.global.ts) and usable as a named middleware.
 * Public routes opt out with `definePageMeta({ public: true })`.
 */
export default defineNuxtRouteMiddleware(async (to) => {
  const auth = useAuthStore()

  // Wait for session restoration before deciding.
  if (auth.status === 'unknown') {
    await auth.restore()
  }

  const isPublic = to.meta.public === true

  if (isPublic) {
    if (auth.isAuthenticated && to.path === '/login') {
      return navigateTo('/dashboard')
    }
    return undefined
  }

  if (!auth.isAuthenticated) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }

  return undefined
})
