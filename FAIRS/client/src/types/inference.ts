export interface GameConfig {
    checkpoint: string;
    datasetName: string;
    sessionId: string;
    initialCapital: number;
    betAmount: number;
}

export interface PredictionResult {
    action: number;
    description: string;
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

export interface SessionState {
    isActive: boolean;
    currentCapital: number;
    currentBet: number;
    lastPrediction: PredictionResult | null;
    totalSteps: number;
}
