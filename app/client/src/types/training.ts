import { RESUME_DEFAULTS, TRAINING_DEFAULTS } from '../generated/trainingDefaults';

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

export const initialTrainingNewConfig: TrainingNewConfig = {
    perceptiveField: TRAINING_DEFAULTS.perceptive_field_size,
    numNeurons: TRAINING_DEFAULTS.qnet_neurons,
    embeddingDims: TRAINING_DEFAULTS.embedding_dimensions,
    explorationRate: TRAINING_DEFAULTS.exploration_rate,
    explorationRateDecay: TRAINING_DEFAULTS.exploration_rate_decay,
    minExplorationRate: TRAINING_DEFAULTS.minimum_exploration_rate,
    discountRate: TRAINING_DEFAULTS.discount_rate,
    modelUpdateFreq: TRAINING_DEFAULTS.model_update_frequency,
    betAmount: TRAINING_DEFAULTS.bet_amount,
    initialCapital: TRAINING_DEFAULTS.initial_capital,
    datasetId: TRAINING_DEFAULTS.dataset_id,
    useDataGen: TRAINING_DEFAULTS.use_data_generator,
    numGeneratedSamples: TRAINING_DEFAULTS.num_generated_samples,
    trainSampleSize: TRAINING_DEFAULTS.sample_size,
    validationSize: TRAINING_DEFAULTS.validation_size,
    splitSeed: TRAINING_DEFAULTS.seed,
    episodes: TRAINING_DEFAULTS.episodes,
    maxStepsEpisode: TRAINING_DEFAULTS.max_steps_episode,
    batchSize: TRAINING_DEFAULTS.batch_size,
    learningRate: TRAINING_DEFAULTS.learning_rate,
    trainingSeed: TRAINING_DEFAULTS.training_seed,
    deviceGPU: TRAINING_DEFAULTS.use_device_gpu,
    deviceID: TRAINING_DEFAULTS.device_id,
    useMixedPrecision: TRAINING_DEFAULTS.use_mixed_precision,
    maxMemorySize: TRAINING_DEFAULTS.max_memory_size,
    replayBufferSize: TRAINING_DEFAULTS.replay_buffer_size,
    dynamicBettingEnabled: TRAINING_DEFAULTS.dynamic_betting_enabled,
    betStrategyModelEnabled: TRAINING_DEFAULTS.bet_strategy_model_enabled,
    betStrategyFixedId: TRAINING_DEFAULTS.bet_strategy_fixed_id,
    strategyHoldSteps: TRAINING_DEFAULTS.strategy_hold_steps,
    betUnitEnabled: TRAINING_DEFAULTS.bet_unit !== null,
    betUnit: TRAINING_DEFAULTS.bet_unit ?? TRAINING_DEFAULTS.bet_amount,
    betMaxEnabled: TRAINING_DEFAULTS.bet_max !== null,
    betMax: TRAINING_DEFAULTS.bet_max ?? TRAINING_DEFAULTS.initial_capital,
    betEnforceCapital: TRAINING_DEFAULTS.bet_enforce_capital,
    checkpointName: TRAINING_DEFAULTS.checkpoint_name ?? '',
};

export interface TrainingResumeConfig {
    selectedCheckpoint: string;
    numAdditionalEpisodes: number;
}

export const initialTrainingResumeConfig: TrainingResumeConfig = {
    selectedCheckpoint: '',
    numAdditionalEpisodes: RESUME_DEFAULTS.additional_episodes,
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
