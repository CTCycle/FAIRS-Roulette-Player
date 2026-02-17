import type { TrainingNewConfig } from '../../../context/AppStateContext';

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
