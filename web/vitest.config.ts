import { fileURLToPath } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '~': fileURLToPath(new URL('./app', import.meta.url)),
      '@': fileURLToPath(new URL('./app', import.meta.url)),
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    include: ['tests/unit/**/*.spec.ts'],
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reportsDirectory: './coverage',
      include: ['app/utils/**', 'app/services/**', 'app/stores/**', 'app/mocks/**'],
    },
  },
})
