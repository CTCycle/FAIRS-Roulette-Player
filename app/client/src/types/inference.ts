import type { FileMetadata } from './datasetUpload';

export interface GameConfig {
    checkpoint: string;
    datasetId: number;
    sessionId: string;
    initialCapital: number;
    betAmount: number;
}

export interface PredictionResult {
    action: number;
    description: string;
    relativePreference?: number;
    confidence?: number;
    betStrategyId?: number;
    betStrategyName?: string;
    suggestedBetAmount?: number;
    currentBetAmount?: number;
}

export interface GameStep {
    step: number;
    predictedAction: number;
    predictedActionDesc: string;
    predictedConfidence?: number;
    observed: number | null;
    observedInput: string;
    betAmount: number;
    outcome: number | null; // profit/loss
    capitalAfter: number | null;
    isEditing: boolean;
}

export interface InferenceSetupState {
    initialCapital: number;
    betAmount: number;
    checkpoint: string;
    selectedDataset: number | null;
    uploadedDatasetId: number | null;
    datasetFileMetadata: FileMetadata | null;
}

export interface InferenceSessionSnapshot {
    config: GameConfig | null;
    isActive: boolean;
    currentCapital: number;
    currentBet: number;
    lastPrediction: PredictionResult | null;
    totalSteps: number;
    history: GameStep[];
}
