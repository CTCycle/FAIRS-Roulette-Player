export interface GameConfig {
    initialCapital: number;
    betAmount: number;
    checkpoint: string;
    datasetName: string;
    sessionId: string;
    initialPrediction: PredictionResult;
}

export interface PredictionResult {
    action: number;
    description: string;
    confidence?: number;
}

export interface GameStep {
    step: number;
    realExtraction: number;
    predictedAction: number;
    predictedActionDesc: string;
    betAmount: number;
    outcome: number; // profit/loss
    capitalAfter: number;
    timestamp: string;
}

export interface SessionState {
    isActive: boolean;
    currentCapital: number;
    currentBet: number;
    history: GameStep[];
    lastPrediction: PredictionResult | null;
    totalSteps: number;
}
