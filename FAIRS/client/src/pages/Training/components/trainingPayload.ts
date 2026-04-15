import type { TrainingNewConfig } from '../../../context/AppStateContext';

const MAX_CHECKPOINT_NAME_LENGTH = 128;

export const buildTrainingPayload = (
    config: TrainingNewConfig,
    datasetIdOverride?: string,
): Record<string, unknown> => {
    const checkpointName = config.checkpointName.trim();
    const rawDatasetId = (datasetIdOverride ?? config.datasetName ?? '').trim();
    const datasetId = /^\d+$/.test(rawDatasetId) ? Number(rawDatasetId) : undefined;
    return ({
    // Agent
    perceptive_field_size: Number(config.perceptiveField),
    QNet_neurons: Number(config.numNeurons),
    embedding_dimensions: Number(config.embeddingDims),
    exploration_rate: Number(config.explorationRate),
    exploration_rate_decay: Number(config.explorationRateDecay),
    minimum_exploration_rate: Number(config.minExplorationRate),
    discount_rate: Number(config.discountRate),
    model_update_frequency: Number(config.modelUpdateFreq),
    // Environment
    bet_amount: Number(config.betAmount),
    initial_capital: Number(config.initialCapital),
    dynamic_betting_enabled: config.dynamicBettingEnabled,
    bet_strategy_model_enabled: config.betStrategyModelEnabled,
    bet_strategy_fixed_id: Number(config.betStrategyFixedId),
    strategy_hold_steps: Number(config.strategyHoldSteps),
    bet_unit: config.betUnitEnabled ? Number(config.betUnit) : undefined,
    bet_max: config.betMaxEnabled ? Number(config.betMax) : undefined,
    bet_enforce_capital: config.betEnforceCapital,
    // Dataset
    dataset_id: datasetId,
    use_data_generator: config.useDataGen,
    num_generated_samples: Number(config.numGeneratedSamples),
    sample_size: Number(config.trainSampleSize),
    validation_size: Number(config.validationSize),
    seed: Number(config.splitSeed),
    // Session
    episodes: Number(config.episodes),
    max_steps_episode: Number(config.maxStepsEpisode),
    batch_size: Number(config.batchSize),
    learning_rate: Number(config.learningRate),
    training_seed: Number(config.trainingSeed),
    use_device_gpu: config.deviceGPU,
    device_id: Number(config.deviceID),
    use_mixed_precision: config.useMixedPrecision,
    // Memory
    max_memory_size: Number(config.maxMemorySize),
    replay_buffer_size: Number(config.replayBufferSize),
    checkpoint_name: checkpointName.length > 0 ? checkpointName : undefined,
    });
};

const isFiniteNumber = (value: number) => Number.isFinite(value);

const validateRange = (
    value: number,
    label: string,
    minimum: number,
    maximum?: number,
): string | null => {
    if (!isFiniteNumber(value) || value < minimum) {
        return `${label} must be at least ${minimum}.`;
    }
    if (maximum !== undefined && value > maximum) {
        return `${label} must be at most ${maximum}.`;
    }
    return null;
};

export const validateTrainingStep = (
    config: TrainingNewConfig,
    datasetIdOverride: string | undefined,
    step: number,
): string | null => {
    switch (step) {
        case 0:
            return (
                validateRange(Number(config.perceptiveField), 'Perceptive field', 1, 1024)
                ?? validateRange(Number(config.numNeurons), 'QNet neurons', 1, 10000)
                ?? validateRange(Number(config.embeddingDims), 'Embedding dimensions', 8)
                ?? validateRange(Number(config.modelUpdateFreq), 'Update frequency', 1)
                ?? validateRange(Number(config.explorationRate), 'Explore rate', 0, 1)
                ?? validateRange(Number(config.explorationRateDecay), 'Decay', 0, 1)
                ?? validateRange(Number(config.minExplorationRate), 'Min explore rate', 0, 1)
                ?? validateRange(Number(config.discountRate), 'Discount rate', 0, 1)
            );
        case 1:
            return (
                validateRange(Number(config.betAmount), 'Bet amount', 1)
                ?? validateRange(Number(config.initialCapital), 'Initial capital', 1)
                ?? validateRange(Number(config.maxMemorySize), 'Max memory', 100)
                ?? validateRange(Number(config.replayBufferSize), 'Replay buffer', 100)
            );
        case 2:
            if (!config.dynamicBettingEnabled) {
                return null;
            }
            return (
                validateRange(Number(config.strategyHoldSteps), 'Strategy hold steps', 1)
                ?? (config.betUnitEnabled ? validateRange(Number(config.betUnit), 'Bet unit', 1) : null)
                ?? (config.betMaxEnabled ? validateRange(Number(config.betMax), 'Bet max', 1) : null)
            );
        case 3:
            if (config.useDataGen) {
                return validateRange(Number(config.numGeneratedSamples), 'Generated samples', 100);
            }
            if (!isFiniteNumber(Number(config.trainSampleSize)) || Number(config.trainSampleSize) <= 0 || Number(config.trainSampleSize) > 1) {
                return 'Sample size must be greater than 0 and at most 1.';
            }
            if (!isFiniteNumber(Number(config.validationSize)) || Number(config.validationSize) < 0 || Number(config.validationSize) >= 1) {
                return 'Validation split must be between 0 and less than 1.';
            }
            return (
                (!datasetIdOverride ? 'Select a dataset to continue.' : null)
            );
        case 4:
            return (
                validateRange(Number(config.episodes), 'Episodes', 1)
                ?? validateRange(Number(config.maxStepsEpisode), 'Max steps', 100)
                ?? validateRange(Number(config.batchSize), 'Batch size', 1)
                ?? (Number(config.learningRate) > 0 ? null : 'Learning rate must be greater than 0.')
                ?? validateRange(Number(config.deviceID), 'Device ID', 0)
            );
        case 5: {
            const checkpointName = config.checkpointName.trim();
            if (!checkpointName) {
                return null;
            }
            if (checkpointName.length > MAX_CHECKPOINT_NAME_LENGTH) {
                return `Checkpoint name must be at most ${MAX_CHECKPOINT_NAME_LENGTH} characters.`;
            }
            if (/[/\\:]/.test(checkpointName) || checkpointName === '.' || checkpointName === '..') {
                return 'Checkpoint name contains invalid characters.';
            }
            return null;
        }
        default:
            return null;
    }
};

export const validateTrainingConfig = (
    config: TrainingNewConfig,
    datasetIdOverride?: string,
): string | null => {
    for (let step = 0; step <= 5; step += 1) {
        const error = validateTrainingStep(config, datasetIdOverride, step);
        if (error) {
            return error;
        }
    }
    return null;
};
