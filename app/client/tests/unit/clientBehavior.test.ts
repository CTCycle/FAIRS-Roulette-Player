// Copyright © 2023 Thomas Virdis
// Licensed under the MIT License.

import { afterEach, describe, expect, it, vi } from 'vitest'
import { initialTrainingNewConfig } from '../../src/types/training'
import { buildTrainingPayload } from '../../src/pages/Training/components/trainingPayload'
import {
    clearPersistedInferenceSession,
    loadPersistedInferenceSession,
    persistInferenceSession,
} from '../../src/utils/inferenceSessionStorage'
import type { GameConfig, InferenceSetupState } from '../../src/types/inference'
import { parseApiErrorDetail, parseDatasetId } from '../../src/utils/apiParsers'

describe('buildTrainingPayload', () => {
    it('converts numeric form values, trims checkpoint names, and applies a dataset override', () => {
        const payload = buildTrainingPayload({
            ...initialTrainingNewConfig,
            perceptiveField: 8,
            numNeurons: 128,
            betAmount: 2,
            datasetId: 3,
            checkpointName: '  qa-checkpoint  ',
        }, 42)

        expect(payload.perceptive_field_size).toBe(8)
        expect(payload.qnet_neurons).toBe(128)
        expect(payload.bet_amount).toBe(2)
        expect(payload.dataset_id).toBe(42)
        expect(payload.checkpoint_name).toBe('qa-checkpoint')
    })

    it('omits optional bet limits when their controls are disabled', () => {
        const payload = buildTrainingPayload({
            ...initialTrainingNewConfig,
            betUnitEnabled: false,
            betMaxEnabled: false,
        })

        const wirePayload = JSON.parse(JSON.stringify(payload)) as Record<string, unknown>
        expect(wirePayload).not.toHaveProperty('bet_unit')
        expect(wirePayload).not.toHaveProperty('bet_max')
    })
})

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

describe('API response parsers', () => {
    it.each([
        [1, 1],
        [0, null],
        [-1, null],
        [1.5, null],
        ['1', null],
    ])('parses dataset id %s as %s', (value, expected) => {
        expect(parseDatasetId(value)).toBe(expected)
    })

    it('formats FastAPI field errors with their locations', () => {
        expect(parseApiErrorDetail({
            detail: [{ loc: ['body', 'episodes'], msg: 'Input should be greater than 0' }],
        }, 'Request failed.')).toBe('body.episodes: Input should be greater than 0')
    })

    it('uses the fallback when a payload has no readable detail', () => {
        expect(parseApiErrorDetail({ detail: [] }, 'Request failed.')).toBe('Request failed.')
    })
})
