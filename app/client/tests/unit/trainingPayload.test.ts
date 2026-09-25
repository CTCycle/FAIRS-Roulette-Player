import { describe, expect, it } from 'vitest'
import { initialTrainingNewConfig } from '../../src/types/training'
import { buildTrainingPayload } from '../../src/pages/Training/components/trainingPayload'

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
