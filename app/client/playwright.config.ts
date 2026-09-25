import { defineConfig } from '@playwright/test'

const baseURL = process.env.FRONTEND_E2E_BASE_URL ?? 'http://127.0.0.1:4173'
const browserChannel = process.env.FRONTEND_E2E_BROWSER_CHANNEL
const browserProfile = browserChannel === 'msedge' ? 'edge' : 'chromium'

export default defineConfig({
    testDir: './tests/e2e',
    fullyParallel: false,
    workers: 1,
    reporter: [
        ['list'],
        ['junit', { outputFile: `../../assets/QA/frontend-e2e-junit-${browserProfile}.xml` }],
    ],
    outputDir: '../../assets/QA/frontend-e2e-artifacts',
    use: {
        baseURL,
        browserName: 'chromium',
        ...(browserChannel ? { channel: browserChannel } : {}),
        viewport: { width: 1280, height: 900 },
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
    },
})
