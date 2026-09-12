import { config } from '@vue/test-utils'
import * as vue from 'vue'

/**
 * Vitest runs the source without Nuxt's auto-import transform, so the globals
 * Nuxt would normally inject (`ref`, `computed`, `useCookie`, …) are provided
 * here. This keeps components/stores under test identical to production code.
 */
const vueGlobals = {
  ref: vue.ref,
  shallowRef: vue.shallowRef,
  reactive: vue.reactive,
  computed: vue.computed,
  watch: vue.watch,
  watchEffect: vue.watchEffect,
  nextTick: vue.nextTick,
  toValue: vue.toValue,
  useId: vue.useId,
  onMounted: vue.onMounted,
  onUnmounted: vue.onUnmounted,
  onBeforeUnmount: vue.onBeforeUnmount,
  h: vue.h,
}

Object.assign(globalThis, vueGlobals)

// Minimal Nuxt composable stubs.
const cookieStore = new Map<string, unknown>()
Object.assign(globalThis, {
  useCookie: (name: string) => {
    if (!cookieStore.has(name)) cookieStore.set(name, vue.ref(null))
    return cookieStore.get(name) as vue.Ref<unknown>
  },
  useRuntimeConfig: () => ({
    public: {
      apiBaseUrl: 'http://localhost:8000',
      wsBaseUrl: 'ws://localhost:8000',
      useMockApi: true,
      appName: 'Aegis Trader',
      appVersion: '0.1.0',
    },
  }),
  useHead: () => undefined,
  navigateTo: () => Promise.resolve(),
  defineNuxtRouteMiddleware: (fn: unknown) => fn,
  definePageMeta: () => undefined,
  useColorMode: () => ({ preference: 'dark' }),
  useRoute: () => ({ path: '/', params: {}, query: {} }),
  useRouter: () => ({ push: () => Promise.resolve() }),
})

// Render <Teleport> content inline so dialogs are queryable in unit tests.
config.global.stubs = {
  teleport: true,
}

// Nuxt UI components are not registered in the plain Vitest environment; stub
// the ones used by isolated (dependency-light) components under test.
config.global.components = {
  UApp: { template: '<div><slot /></div>' },
  UButton: {
    props: ['disabled', 'loading'],
    emits: ['click'],
    template:
      '<button :disabled="disabled" @click="$emit(\'click\')"><slot /><slot name="trailing" /></button>',
  },
  UIcon: { props: ['name'], template: '<span class="icon" :data-name="name" />' },
}
