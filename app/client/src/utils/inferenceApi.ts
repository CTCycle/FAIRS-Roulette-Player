import type { PredictionResult } from '../types/inference';
import { isRecord, parseApiErrorDetail } from './apiParsers';

export interface InferenceSessionStartOptions {
    sessionId?: string;
    checkpoint: string;
    datasetId: number;
    datasetSource: 'source' | 'uploaded' | null;
    gameCapital: number;
    gameBet: number;
}

export type InferenceStartResponse = Record<string, unknown> & {
    prediction: PredictionResult;
};

export type InferenceNextResponse = Record<string, unknown> & {
    prediction: PredictionResult;
};

export type InferenceStepResponse = Record<string, unknown>;

const maybeNumber = (value: unknown): number | undefined => {
    if (value === null || value === undefined || value === '') {
        return undefined;
    }
    if (typeof value === 'boolean') {
        return undefined;
    }
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
};

const normalizePrediction = (value: unknown): PredictionResult => {
    const payload = isRecord(value) ? value : {};
    const betStrategyName = typeof payload.bet_strategy_name === 'string'
        ? payload.bet_strategy_name
        : (typeof payload.betStrategyName === 'string' ? payload.betStrategyName : undefined);

    return {
        action: maybeNumber(payload.action) ?? 0,
        description: typeof payload.description === 'string' ? payload.description : 'Unknown',
        confidence: maybeNumber(payload.confidence),
        betStrategyId: maybeNumber(payload.bet_strategy_id ?? payload.betStrategyId),
        betStrategyName,
        suggestedBetAmount: maybeNumber(payload.suggested_bet_amount ?? payload.suggestedBetAmount),
        currentBetAmount: maybeNumber(payload.current_bet_amount ?? payload.currentBetAmount),
    };
};

const readJson = async (response: Response): Promise<unknown> => (
    response.json().catch(() => null)
);

const requestJson = async (
    endpoint: string,
    init: RequestInit,
    fallbackMessage: string,
): Promise<Record<string, unknown>> => {
    const response = await fetch(endpoint, init);
    const payload = await readJson(response);
    if (!response.ok) {
        throw new Error(parseApiErrorDetail(payload, fallbackMessage));
    }
    return isRecord(payload) ? payload : {};
};

export const uploadInferenceDataset = async (file: File): Promise<Record<string, unknown>> => {
    const formData = new FormData();
    formData.append('file', file);
    return requestJson(
        '/api/data/upload?dataset_kind=inference',
        { method: 'POST', body: formData },
        'Upload failed.',
    );
};

export const clearInferenceContext = async (): Promise<Record<string, unknown>> => (
    requestJson('/api/inference/context/clear', { method: 'POST' }, 'Unable to clear inference context.')
);

export const startInferenceSession = async (
    options: InferenceSessionStartOptions,
): Promise<InferenceStartResponse> => {
    const payload = await requestJson(
        '/api/inference/sessions/start',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: options.sessionId,
                checkpoint: options.checkpoint,
                dataset_id: options.datasetId,
                dataset_source: options.datasetSource,
                game_capital: options.gameCapital,
                game_bet: options.gameBet,
            }),
        },
        'Session start failed.',
    );
    return { ...payload, prediction: normalizePrediction(payload.prediction) };
};

export const shutdownInferenceSession = async (
    sessionId: string,
): Promise<Record<string, unknown>> => (
    requestJson(
        `/api/inference/sessions/${sessionId}/shutdown`,
        { method: 'POST' },
        'Stop failed.',
    )
);

export const clearInferenceSessionRows = async (
    sessionId: string,
): Promise<Record<string, unknown>> => (
    requestJson(
        `/api/inference/sessions/${sessionId}/rows/clear`,
        { method: 'POST' },
        'Unable to clear session rows.',
    )
);

export const updateInferenceBet = async (
    sessionId: string,
    betAmount: number,
): Promise<Record<string, unknown>> => (
    requestJson(
        `/api/inference/sessions/${sessionId}/bet`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bet_amount: betAmount }),
        },
        'Bet update failed.',
    )
);

export const requestNextInferencePrediction = async (
    sessionId: string,
): Promise<InferenceNextResponse> => {
    const payload = await requestJson(
        `/api/inference/sessions/${sessionId}/next`,
        { method: 'POST' },
        'Prediction failed.',
    );
    return { ...payload, prediction: normalizePrediction(payload.prediction) };
};

export const submitInferenceStep = async (
    sessionId: string,
    extraction: number,
): Promise<InferenceStepResponse> => (
    requestJson(
        `/api/inference/sessions/${sessionId}/step`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ extraction }),
        },
        'Step failed.',
    )
);

export { normalizePrediction };
