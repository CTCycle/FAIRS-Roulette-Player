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
    perceptiveField: 64,
    numNeurons: 64,
    embeddingDims: 200,
    explorationRate: 0.75,
    explorationRateDecay: 0.995,
    minExplorationRate: 0.10,
    discountRate: 0.50,
    modelUpdateFreq: 10,
    betAmount: 10,
    initialCapital: 1000,
    datasetId: null,
    useDataGen: false,
    numGeneratedSamples: 10000,
    trainSampleSize: 1.0,
    validationSize: 0.20,
    splitSeed: 42,
    episodes: 10,
    maxStepsEpisode: 2000,
    batchSize: 32,
    learningRate: 0.0001,
    trainingSeed: 42,
    deviceGPU: false,
    deviceID: 0,
    useMixedPrecision: false,
    maxMemorySize: 10000,
    replayBufferSize: 1000,
    dynamicBettingEnabled: false,
    betStrategyModelEnabled: false,
    betStrategyFixedId: 0,
    strategyHoldSteps: 1,
    betUnitEnabled: false,
    betUnit: 10,
    betMaxEnabled: false,
    betMax: 1000,
    betEnforceCapital: true,
    checkpointName: '',
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
