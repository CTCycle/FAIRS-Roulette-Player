import path from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
const envDir = path.resolve(__dirname, '../settings')
const INTERNAL_API_BASE = '/api'

export default defineConfig(({ mode }) => {
    const settingsEnv = loadEnv(mode, envDir, '')
    const clientEnv = loadEnv(mode, process.cwd(), '')
    const env = { ...clientEnv, ...process.env, ...settingsEnv }

    const apiHost = env.FASTAPI_HOST || '127.0.0.1'
    const apiPort = env.FASTAPI_PORT || '8000'
    const apiTarget = `http://${apiHost}:${apiPort}`
    const apiBase = (env.VITE_API_BASE_URL || '/api').trim() || '/api'
    if (!apiBase.startsWith('/') || apiBase.startsWith('//') || /^[a-z]+:\/\//i.test(apiBase)) {
        throw new Error('VITE_API_BASE_URL must be a relative API path like /api')
    }
    const apiBasePattern = new RegExp(`^${apiBase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`)

    const uiHost = env.UI_HOST || '127.0.0.1'
    const uiPort = Number(env.UI_PORT || '5173')

    return {
        plugins: [react()],
        server: {
            host: uiHost,
            port: uiPort,
            strictPort: false,
            proxy: {
                [apiBase]: {
                    target: apiTarget,
                    changeOrigin: true,
                    rewrite: (requestPath) => requestPath.replace(apiBasePattern, INTERNAL_API_BASE),
                },
            },
        },
        preview: {
            host: uiHost,
            port: uiPort,
            strictPort: false,
            proxy: {
                [apiBase]: {
                    target: apiTarget,
                    changeOrigin: true,
                    rewrite: (requestPath) => requestPath.replace(apiBasePattern, INTERNAL_API_BASE),
                },
            },
        },
    }
})
