import { afterEach, describe, expect, it, vi } from 'vitest'
import {
    clearPersistedInferenceSession,
    loadPersistedInferenceSession,
    persistInferenceSession,
} from '../../src/utils/inferenceSessionStorage'
import type { GameConfig, InferenceSetupState } from '../../src/types/inference'

const key = 'fairs.roulette.inference-session.v1'

const createStorage = () => {
    const values = new Map<string, string>()
    return {
        getItem: (name: string) => values.get(name) ?? null,
        setItem: (name: string, value: string) => values.set(name, value),
        removeItem: (name: string) => values.delete(name),
        values,
    }
}

const config: GameConfig = {
    sessionId: 'session-1',
    checkpoint: 'checkpoint-1',
    datasetId: 7,
    initialCapital: 100,
    betAmount: 2,
}

const setup: InferenceSetupState = {
    initialCapital: 100,
    betAmount: 2,
    checkpoint: 'checkpoint-1',
    selectedDataset: 7,
    uploadedDatasetId: null,
    datasetFileMetadata: null,
}

afterEach(() => vi.unstubAllGlobals())

describe('inference session storage', () => {
    it('round-trips a versioned session and clears it', () => {
        const localStorage = createStorage()
        vi.stubGlobal('window', { localStorage })

        persistInferenceSession(config, setup)
        expect(localStorage.values.has(key)).toBe(true)
        expect(loadPersistedInferenceSession()).toEqual({ version: 1, config, setup })

        clearPersistedInferenceSession()
        expect(loadPersistedInferenceSession()).toBeNull()
    })

    it('removes malformed session shapes instead of restoring them', () => {
        const localStorage = createStorage()
        localStorage.setItem(key, JSON.stringify({ version: 1, config: {}, setup: {} }))
        vi.stubGlobal('window', { localStorage })

        expect(loadPersistedInferenceSession()).toBeNull()
        expect(localStorage.getItem(key)).toBeNull()
    })
})
