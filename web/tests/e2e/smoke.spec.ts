import { expect, test } from '@playwright/test'

/**
 * Phase 1 smoke tests. These require a running dev server
 * (`npm run dev`) and `npx playwright install chromium`.
 */
test('unauthenticated visitors are redirected to the login page', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/login/)
  await expect(
    page.getByRole('heading', { name: /sign in|create owner account/i }),
  ).toBeVisible()
})

test('login page shows the paper trading environment notice', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByText(/paper trading environment/i)).toBeVisible()
})

test('protected route redirects to login with a redirect target', async ({ page }) => {
  await page.goto('/risk')
  await expect(page).toHaveURL(/\/login/)
  expect(page.url()).toContain('redirect')
})
