import path from 'node:path'

import { expect, test } from '@playwright/test'

const PASSWORD = 'CorrectHorse!42'
const fixture = path.join(import.meta.dirname, 'fixtures', 'biology-notes.pdf')

test('sign up, upload, ask with streaming, stay signed in, sign out', async ({ page, context }) => {
  const email = `e2e-${Date.now()}@example.com`

  // Sign up lands on the overview.
  await page.goto('/signup')
  await page.getByLabel('Full name').fill('Asha Verma')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByLabel('Confirm password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByRole('heading', { name: /Asha/ })).toBeVisible()

  // Tokens never reach JavaScript-readable storage; the refresh cookie is httpOnly.
  const storage = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))
  expect(storage).not.toMatch(/eyJ|token/i)
  const cookie = (await context.cookies()).find((c) => c.name === 'ns_refresh')
  expect(cookie?.httpOnly).toBe(true)
  expect(cookie?.sameSite).toBe('Strict')
  expect(await page.evaluate(() => document.cookie)).not.toContain('ns_refresh')

  // Upload a PDF; the worker processes it.
  await page
    .getByRole('link', { name: /Documents/ })
    .first()
    .click()
  await page.locator('input[type=file]').first().setInputFiles(fixture)
  await expect(page.getByText('biology-notes.pdf')).toBeVisible()
  await expect(page.getByText('Ready', { exact: true })).toBeVisible({ timeout: 60_000 })

  // Ask a question; the answer streams in with sources.
  await page
    .getByRole('link', { name: /AI Chat/ })
    .first()
    .click()
  await page.getByLabel('Your question').fill('Where does photosynthesis take place?')
  await page.getByRole('button', { name: 'Send question' }).click()
  await expect(page.getByText(/chloroplast/i).first()).toBeVisible({ timeout: 90_000 })
  await expect(page.getByText('Sources', { exact: true })).toBeVisible({ timeout: 90_000 })
  await expect(page).toHaveURL(/\/chat\/[0-9a-f-]{36}/)

  // A reload keeps the session (silent refresh from the cookie) and the history.
  await page.reload()
  await expect(page.getByText('Where does photosynthesis take place?').first()).toBeVisible()

  // Sign out ends the session; a reload doesn't bring it back.
  await page.getByRole('link', { name: 'Settings' }).click()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL(/\/login/)
  await page.goto('/')
  await expect(page).toHaveURL(/\/login/)
})

test('protected pages redirect to login and come back after signing in', async ({ page, request }) => {
  const email = `e2e-redirect-${Date.now()}@example.com`
  await request.post('/api/v1/auth/signup', { data: { name: 'Ravi Kumar', email, password: PASSWORD } })

  await page.goto('/search?q=plants')
  await expect(page).toHaveURL(/\/login/)
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/search\?q=plants/)
})

test('wrong password shows the server message', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill('nobody@example.com')
  await page.getByLabel('Password').fill('WrongPassword1')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('alert')).toContainText('Invalid email or password')
})
