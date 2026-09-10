import { TRAINING_CONFIG_DEFAULTS } from '../generated/api';

export interface TrainingNewConfig {
    perceptiveField: number;
    numNeurons: number;
    embeddingDims: number;
    explorationRate: number;
    explorationRateDecay: number;
    minExplorationRate: number;
    discountRate: number;
    modelUpdateFreq: number;
    betAmount: number;
    initialCapital: number;
    datasetId: number | null;
    useDataGen: boolean;
    numGeneratedSamples: number;
    trainSampleSize: number;
    validationSize: number;
    splitSeed: number;
    episodes: number;
    maxStepsEpisode: number;
    batchSize: number;
    learningRate: number;
    trainingSeed: number;
    deviceGPU: boolean;
    deviceID: number;
    useMixedPrecision: boolean;
    maxMemorySize: number;
    replayBufferSize: number;
    dynamicBettingEnabled: boolean;
    betStrategyModelEnabled: boolean;
    betStrategyFixedId: number;
    strategyHoldSteps: number;
    betUnitEnabled: boolean;
    betUnit: number;
    betMaxEnabled: boolean;
    betMax: number;
    betEnforceCapital: boolean;
    checkpointName: string;
}

const defaults = TRAINING_CONFIG_DEFAULTS;

export const initialTrainingNewConfig: TrainingNewConfig = {
    perceptiveField: defaults.perceptive_field_size,
    numNeurons: defaults.qnet_neurons,
    embeddingDims: defaults.embedding_dimensions,
    explorationRate: defaults.exploration_rate,
    explorationRateDecay: defaults.exploration_rate_decay,
    minExplorationRate: defaults.minimum_exploration_rate,
    discountRate: defaults.discount_rate,
    modelUpdateFreq: defaults.model_update_frequency,
    betAmount: defaults.bet_amount,
    initialCapital: defaults.initial_capital,
    datasetId: defaults.dataset_id,
    useDataGen: defaults.use_data_generator,
    numGeneratedSamples: defaults.num_generated_samples,
    trainSampleSize: defaults.sample_size,
    validationSize: defaults.validation_size,
    splitSeed: defaults.seed,
    episodes: defaults.episodes,
    maxStepsEpisode: defaults.max_steps_episode,
    batchSize: defaults.batch_size,
    learningRate: defaults.learning_rate,
    trainingSeed: defaults.training_seed,
    deviceGPU: defaults.use_device_gpu,
    deviceID: defaults.device_id,
    useMixedPrecision: defaults.use_mixed_precision,
    maxMemorySize: defaults.max_memory_size,
    replayBufferSize: defaults.replay_buffer_size,
    dynamicBettingEnabled: defaults.dynamic_betting_enabled,
    betStrategyModelEnabled: defaults.bet_strategy_model_enabled,
    betStrategyFixedId: defaults.bet_strategy_fixed_id,
    strategyHoldSteps: defaults.strategy_hold_steps,
    betUnitEnabled: defaults.bet_unit !== null,
    betUnit: defaults.bet_unit ?? defaults.bet_amount,
    betMaxEnabled: defaults.bet_max !== null,
    betMax: defaults.bet_max ?? defaults.initial_capital,
    betEnforceCapital: defaults.bet_enforce_capital,
    checkpointName: defaults.checkpoint_name ?? '',
};

export interface TrainingResumeConfig {
    selectedCheckpoint: string;
    numAdditionalEpisodes: number;
}

export const initialTrainingResumeConfig: TrainingResumeConfig = {
    selectedCheckpoint: '',
    numAdditionalEpisodes: 10,
};

export type TrainingStatusCode =
    | 'idle'
    | 'exploration'
    | 'training'
    | 'completed'
    | 'error'
    | 'cancelled'
    | 'stopping';

export interface TrainingHistoryPoint {
    time_step: number;
    loss: number;
    rmse: number;
    epoch: number;
    val_loss?: number | null;
    val_rmse?: number | null;
    val_reward?: number | null;
    epsilon?: number | null;
    experience_count?: number;
    replay_buffer_size?: number;
    reward?: number;
    total_reward?: number;
    capital?: number;
    capital_gain?: number;
}

export interface TrainingStats {
    epoch: number;
    total_epochs: number;
    max_steps: number;
    time_step: number;
    loss: number | null;
    rmse: number | null;
    val_loss: number | null;
    val_rmse: number | null;
    reward: number;
    val_reward: number | null;
    total_reward: number;
    capital: number;
    capital_gain: number;
    current_bet_amount: number | null;
    current_strategy_id: number | null;
    current_strategy_name?: string;
    epsilon: number | null;
    experience_count: number;
    replay_buffer_size: number;
    status: TrainingStatusCode;
    message?: string;
}

export interface TrainingStatusSnapshot {
    job_id: string | null;
    is_training: boolean;
    latest_stats: TrainingStats;
    history: TrainingHistoryPoint[];
    latest_env: Record<string, unknown>;
    poll_interval: number;
}
