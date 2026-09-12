// Nuxt 4 configuration for the Aegis Trader browser terminal.
//
// Architecture notes:
// - `ssr: false` (SPA): this is an authenticated, real-time control surface
//   driven by a bearer-token session and a persistent WebSocket. Rendering on
//   the client avoids hydration/auth-token duplication. The backend remains the
//   single source of truth. Revisit SSR in a later phase if cookie-based auth is
//   added.
// - Tailwind v4 is CSS-first (design tokens live in app/assets/css/main.css),
//   so no tailwind.config.ts is required.
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',

  ssr: false,

  devtools: { enabled: true },

  modules: ['@nuxt/ui', '@pinia/nuxt', '@vueuse/nuxt', '@nuxt/eslint'],

  css: ['~/assets/css/main.css'],

  // Register components without path prefixes so `<MetricCard>` (not
  // `<UiMetricCard>`) is used everywhere.
  components: [{ path: '~/components', pathPrefix: false }],

  typescript: {
    strict: true,
    typeCheck: true,
  },

  // Dark-first professional terminal theme. `@nuxt/ui` bundles color-mode.
  colorMode: {
    preference: 'dark',
    fallback: 'dark',
    classSuffix: '',
    storageKey: 'aegis-color-mode',
  },

  ui: {
    // Avoid remote font fetching; numeric-heavy terminals use a system stack.
    fonts: false,
  },

  runtimeConfig: {
    public: {
      apiBaseUrl: 'http://localhost:8000',
      wsBaseUrl: 'ws://localhost:8000',
      useMockApi: false,
      appName: 'Aegis Trader',
      appVersion: '0.1.0',
    },
  },

  app: {
    head: {
      title: 'Aegis Trader',
      titleTemplate: '%s · Aegis Trader',
      htmlAttrs: { lang: 'en' },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content: 'AI-assisted, risk-gated automated trading terminal (paper trading).',
        },
        { name: 'theme-color', content: '#0b0f14' },
      ],
    },
  },

  eslint: {
    config: {
      stylistic: false,
    },
  },
})
