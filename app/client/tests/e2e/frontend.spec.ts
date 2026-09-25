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

test('Settings save feedback follows the mocked update response', async ({ page }) => {
    await page.goto('/settings')
    const maximum = page.getByLabel('Maximum', { exact: true })
    await expect(maximum).toHaveValue('36')
    await maximum.fill('35')
    await page.getByRole('button', { name: 'Save settings', exact: true }).click()
    await expect(page.getByRole('status')).toHaveText('Settings saved.')
    await expect(maximum).toHaveValue('35')
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
