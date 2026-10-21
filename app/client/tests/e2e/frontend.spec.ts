// Copyright © 2023 Thomas Virdis
// Licensed under the MIT License.

import { expect, test, type Page } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const settings = () => ({
    jobs: { polling_interval: 1 },
    device: { jit_compile: false, jit_backend: 'eager' },
    roulette: {
        minimum_number: 0,
        maximum_number: 36,
        exclude_zero: false,
        invert_colors: false,
        show_number_labels: true,
    },
})

const installApiMocks = async (page: Page) => {
    let currentSettings = settings()
    let databaseConfiguration = {
        backend: 'sqlite' as 'sqlite' | 'postgresql',
        sqlite_path: 'data/database.db',
        host: '',
        port: 5432,
        database_name: '',
        username: '',
        password_configured: false,
        ssl: false,
        ssl_ca: '',
        connect_timeout: 10,
        insert_batch_size: 1000,
    }
    const databaseStatus = () => ({
        configuration: databaseConfiguration,
        active_backend: databaseConfiguration.backend,
        status: 'ready',
        message: null,
    })
    await page.route('**/api/**', async (route) => {
        const request = route.request()
        const url = new URL(request.url())
        const method = request.method()
        const json = (body: unknown, status = 200) => route.fulfill({
            status,
            contentType: 'application/json',
            body: JSON.stringify(body),
        })

        if (url.pathname === '/api/health') {
            return json({ status: 'ok', application: 'FAIRS', version: '3.4.2' })
        }
        if (url.pathname === '/api/training/status') {
            return json({
                job_id: null,
                is_training: false,
                latest_stats: {
                    epoch: 0,
                    total_epochs: 0,
                    max_steps: 0,
                    time_step: 0,
                    loss: null,
                    rmse: null,
                    val_loss: null,
                    val_rmse: null,
                    reward: 0,
                    val_reward: null,
                    total_reward: 0,
                    capital: 0,
                    capital_gain: 0,
                    current_bet_amount: null,
                    current_strategy_id: null,
                    epsilon: null,
                    experience_count: 0,
                    replay_buffer_size: 0,
                    status: 'idle',
                },
                history: [],
                latest_env: {},
                poll_interval: 1,
            })
        }
        if (url.pathname === '/api/datasets/training/summary') {
            return json({ datasets: [{ dataset_id: 7, dataset_name: 'Frontend fixture', row_count: 100 }] })
        }
        if (url.pathname === '/api/training/checkpoints') {
            return json(['frontend-checkpoint'])
        }
        if (url.pathname === '/api/training/checkpoints/frontend-checkpoint/metadata') {
            return json({
                checkpoint: 'frontend-checkpoint',
                summary: {
                    batch_size: 16,
                    bet_amount: 1,
                    dataset_id: 7,
                    discount_rate: 0.95,
                    embedding_dimensions: 16,
                    episodes: 10,
                    exploration_rate: 1,
                    exploration_rate_decay: 0.99,
                    final_loss: null,
                    initial_capital: 100,
                    learning_rate: 0.001,
                    max_memory_size: 100,
                    max_steps_episode: 10,
                    minimum_exploration_rate: 0.01,
                    model_update_frequency: 1,
                    perceptive_field_size: 4,
                    qnet_neurons: 32,
                    replay_buffer_size: 100,
                },
            })
        }
        if (url.pathname === '/api/settings' && method === 'GET') {
            return json(currentSettings)
        }
        if (url.pathname === '/api/settings' && method === 'PATCH') {
            const patch = request.postDataJSON() as typeof currentSettings
            currentSettings = {
                ...currentSettings,
                ...patch,
                roulette: { ...currentSettings.roulette, ...patch.roulette },
                jobs: { ...currentSettings.jobs, ...patch.jobs },
                device: { ...currentSettings.device, ...patch.device },
            }
            return json(currentSettings)
        }
        if (url.pathname === '/api/settings/reset' && method === 'POST') {
            currentSettings = settings()
            return json(currentSettings)
        }
        if (url.pathname === '/api/settings/database' && method === 'GET') {
            return json(databaseStatus())
        }
        if (url.pathname === '/api/settings/database/test' && method === 'POST') {
            return json({ success: true, message: 'Connection test succeeded.' })
        }
        if (url.pathname === '/api/settings/database' && method === 'PUT') {
            const candidate = request.postDataJSON() as typeof databaseConfiguration & { password?: string }
            const { password, ...publicCandidate } = candidate
            databaseConfiguration = {
                ...databaseConfiguration,
                ...publicCandidate,
                password_configured: Boolean(password) || databaseConfiguration.password_configured,
            }
            return json(databaseStatus())
        }
        return json({ detail: `Unexpected mocked request: ${method} ${url.pathname}` }, 404)
    })
}

test.beforeEach(async ({ page }) => {
    await installApiMocks(page)
})

test('Training wizard advances and returns to a selected step', async ({ page }) => {
    await page.goto('/training')
    await expect(page.getByText('Connected', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Configure training with this dataset' }).first().click()

    const wizard = page.getByRole('dialog', { name: 'New Training Wizard' })
    await expect(wizard).toBeVisible()
    await expect(wizard.getByText('Step 1 of 6')).toBeVisible()
    await wizard.getByRole('button', { name: 'Next', exact: true }).click()
    await expect(wizard.getByText('Step 2 of 6')).toBeVisible()
    const steps = wizard.getByRole('navigation', { name: 'Training wizard steps' })
    await steps.getByRole('button', { name: /Summary/ }).click()
    await expect(wizard.getByText('Step 6 of 6')).toBeVisible()
    await steps.getByRole('button', { name: /Agent Configuration/ }).click()
    await expect(wizard.getByText('Step 1 of 6')).toBeVisible()
})

test('Inference setup loads checkpoint and dataset options', async ({ page }) => {
    await page.goto('/inference')
    await expect(page.getByLabel('Model checkpoint')).toHaveValue('frontend-checkpoint')
    await expect(page.getByLabel('Inference dataset', { exact: true })).toHaveValue('7')
    await expect(page.getByRole('button', { name: 'Play', exact: true })).toBeEnabled()
})

test('Settings changes save automatically and survive a reload', async ({ page }) => {
    await page.goto('/settings')
    await expect(page.getByRole('button', { name: 'Save settings', exact: true })).toHaveCount(0)
    const maximum = page.getByLabel('Maximum', { exact: true })
    await expect(maximum).toHaveValue('36')
    await maximum.fill('35')
    await expect(page.getByRole('status')).toHaveText('Changes saved.')
    await expect(maximum).toHaveValue('35')
    const minimum = page.getByLabel('Minimum', { exact: true })
    const includeZero = page.getByLabel('Include zero', { exact: true })
    await minimum.fill('3')
    await includeZero.uncheck()
    await expect(page.getByRole('status')).toHaveText('Changes saved.')

    await page.getByRole('button', { name: 'Appearance', exact: true }).click()
    const invert = page.getByLabel('Invert colors', { exact: true })
    const labels = page.getByLabel('Show number labels', { exact: true })
    await invert.check()
    await expect(page.getByRole('status')).toHaveText('Changes saved.')
    await labels.uncheck()
    await expect(page.getByRole('status')).toHaveText('Changes saved.')

    await page.getByRole('button', { name: 'Runtime', exact: true }).click()
    const polling = page.getByLabel('Polling interval', { exact: true })
    await polling.fill('2.5')
    await expect(page.getByRole('status')).toHaveText('Changes saved.')

    await page.getByRole('button', { name: 'Advanced', exact: true }).click()
    const jitCompile = page.getByLabel('Enable JIT compilation', { exact: true })
    const jitBackend = page.getByLabel('JIT backend', { exact: true })
    await jitCompile.check()
    await expect(page.getByRole('status')).toHaveText('Changes saved.')
    await jitBackend.fill('mock-backend')
    await expect(page.getByRole('status')).toHaveText('Changes saved.')

    await page.reload()
    await expect(page.getByLabel('Minimum', { exact: true })).toHaveValue('3')
    await expect(page.getByLabel('Maximum', { exact: true })).toHaveValue('35')
    await expect(page.getByLabel('Include zero', { exact: true })).not.toBeChecked()
    await page.getByRole('button', { name: 'Appearance', exact: true }).click()
    await expect(page.getByLabel('Invert colors', { exact: true })).toBeChecked()
    await expect(page.getByLabel('Show number labels', { exact: true })).not.toBeChecked()
    await page.getByRole('button', { name: 'Runtime', exact: true }).click()
    await expect(page.getByLabel('Polling interval', { exact: true })).toHaveValue('2.5')
    await page.getByRole('button', { name: 'Advanced', exact: true }).click()
    await expect(page.getByLabel('Enable JIT compilation', { exact: true })).toBeChecked()
    await expect(page.getByLabel('JIT backend', { exact: true })).toHaveValue('mock-backend')
})

test('Settings debounces continuous edits and preserves later changes after a failed write', async ({ page }) => {
    const patches: string[] = []
    let failNextPatch = true
    page.on('request', (request) => {
        if (request.method() === 'PATCH' && new URL(request.url()).pathname === '/api/settings') {
            patches.push(request.postData() ?? '')
        }
    })
    await page.route('**/api/settings', async (route) => {
        const patch = route.request().postDataJSON() as { roulette?: { invert_colors?: boolean } } | null;
        if (
            route.request().method() === 'PATCH'
            && failNextPatch
            && patch?.roulette?.invert_colors === true
        ) {
            failNextPatch = false
            await route.fulfill({
                status: 500,
                contentType: 'application/json',
                body: JSON.stringify({ detail: 'Simulated database write failure.' }),
            })
            return
        }
        await route.fallback()
    })

    await page.goto('/settings')
    const polling = page.getByLabel('Polling interval', { exact: true })
    await page.getByRole('button', { name: 'Runtime', exact: true }).click()
    await polling.fill('2.1')
    await polling.fill('3.2')
    await polling.fill('4.3')
    await expect(page.getByRole('status')).toHaveText('Changes saved.')
    expect(patches).toHaveLength(1)
    expect(JSON.parse(patches[0]).jobs.polling_interval).toBe(4.3)

    await page.getByRole('button', { name: 'Appearance', exact: true }).click()
    const invert = page.getByLabel('Invert colors', { exact: true })
    await invert.check()
    await expect(page.getByRole('alert')).toContainText('Change not saved.')
    await page.getByLabel('Show number labels', { exact: true }).uncheck()
    await expect(page.getByRole('status')).toHaveText('Changes saved.')

    await page.reload()
    await page.getByRole('button', { name: 'Runtime', exact: true }).click()
    await expect(page.getByLabel('Polling interval', { exact: true })).toHaveValue('4.3')
    await page.getByRole('button', { name: 'Appearance', exact: true }).click()
    await expect(page.getByLabel('Invert colors', { exact: true })).toBeChecked()
    await expect(page.getByLabel('Show number labels', { exact: true })).not.toBeChecked()
})

test('Settings retries a newer immediate edit queued during a failed write', async ({ page }) => {
    let failNextPatch = true
    let notifyFirstPatchStarted!: () => void
    const firstPatchStarted = new Promise<void>((resolve) => {
        notifyFirstPatchStarted = resolve
    })
    await page.route('**/api/settings', async (route) => {
        const patch = route.request().postDataJSON() as { roulette?: { invert_colors?: boolean } } | null
        if (
            route.request().method() === 'PATCH'
            && failNextPatch
            && patch?.roulette?.invert_colors === true
        ) {
            failNextPatch = false
            notifyFirstPatchStarted()
            await new Promise((resolve) => setTimeout(resolve, 200))
            await route.fulfill({
                status: 500,
                contentType: 'application/json',
                body: JSON.stringify({ detail: 'Simulated database write failure.' }),
            })
            return
        }
        await route.fallback()
    })

    await page.goto('/settings')
    await page.getByRole('button', { name: 'Appearance', exact: true }).click()
    await page.getByLabel('Invert colors', { exact: true }).check()
    await firstPatchStarted
    await page.getByLabel('Show number labels', { exact: true }).uncheck()
    await expect(page.getByRole('status')).toHaveText('Changes saved.')

    await page.reload()
    await page.getByRole('button', { name: 'Appearance', exact: true }).click()
    await expect(page.getByLabel('Invert colors', { exact: true })).toBeChecked()
    await expect(page.getByLabel('Show number labels', { exact: true })).not.toBeChecked()
})

test('Database fields stay as a draft until the explicit switch action', async ({ page }) => {
    await page.goto('/settings?section=database')
    await expect(page.getByText('Active: SQLite', { exact: true })).toBeVisible()
    await page.getByLabel('Backend', { exact: true }).selectOption('postgresql')
    await page.getByLabel('PostgreSQL host', { exact: true }).fill('db.example.test')
    await page.getByLabel('PostgreSQL port', { exact: true }).fill('5433')
    await page.getByLabel('PostgreSQL database name', { exact: true }).fill('fairs_test')
    await page.getByLabel('PostgreSQL username', { exact: true }).fill('fairs_user')
    await page.getByLabel('Password', { exact: true }).fill('secret')
    await page.getByLabel('Require SSL', { exact: true }).check()
    await page.getByLabel('SSL and CA certificate').fill('certs/ca.pem')
    await page.getByLabel('Connection timeout', { exact: true }).fill('15')
    await page.getByLabel('Insert batch size', { exact: true }).fill('2500')

    await page.getByRole('button', { name: 'Advanced', exact: true }).click()
    await page.getByRole('button', { name: 'Database', exact: true }).click()
    await expect(page.getByLabel('PostgreSQL host', { exact: true })).toHaveValue('db.example.test')

    await page.getByRole('button', { name: 'Test connection', exact: true }).click()
    await expect(page.getByText('Connection test succeeded.', { exact: true })).toBeVisible()
    await expect(page.getByText('Active: SQLite', { exact: true })).toBeVisible()
    const beforeConfirmation = await page.evaluate(async () => (
        fetch('/api/settings/database').then((response) => response.json())
    ))
    expect(beforeConfirmation.active_backend).toBe('sqlite')
    expect(beforeConfirmation.configuration.backend).toBe('sqlite')

    await page.getByRole('button', { name: 'Apply and switch', exact: true }).click()
    await expect(page.getByText('Active: PostgreSQL', { exact: true })).toBeVisible()
    await expect(page.getByText('Database activated. Settings were reloaded from that database.', { exact: true })).toBeVisible()
})

test('1100px is supported and 1099px shows the minimum-width notice', async ({ page }) => {
    const evidenceRoot = path.resolve(process.cwd(), '..', '..', 'assets', 'QA')
    await mkdir(evidenceRoot, { recursive: true })
    const browserProfile = process.env.FRONTEND_E2E_BROWSER_CHANNEL === 'msedge' ? 'edge' : 'chromium'
    await page.setViewportSize({ width: 1100, height: 800 })
    await page.goto('/training')
    const minimumWidthNotice = page.getByText(/requires a browser viewport at least 1100px wide/i)
    await expect(minimumWidthNotice).toBeHidden()
    await expect(page.getByText('Available Datasets')).toBeVisible()
    await page.screenshot({ path: path.join(evidenceRoot, `frontend-viewport-1100-${browserProfile}.png`), fullPage: true })

    await page.setViewportSize({ width: 1099, height: 800 })
    await expect(minimumWidthNotice).toBeVisible()
    await page.screenshot({ path: path.join(evidenceRoot, `frontend-viewport-1099-${browserProfile}.png`), fullPage: true })
})
