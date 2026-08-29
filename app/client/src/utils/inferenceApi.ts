import type { PredictionResult } from '../types/inference';
import { isRecord, parseApiErrorDetail, parseDatasetId } from './apiParsers';

export interface InferenceSessionStartOptions {
    checkpoint: string;
    datasetId: number;
    gameCapital: number;
    gameBet: number;
}

export interface InferenceDatasetUploadResponse {
    dataset_id: number | null;
    filename: string;
    rows_imported: number;
    dataset_name: string | null;
    dataset_kind: string | null;
    columns: string[];
}

export interface InferenceStartResponse {
    session_id: string;
    checkpoint: string;
    game_capital: number;
    game_bet: number;
    current_capital: number;
    prediction: PredictionResult;
}

export interface InferenceNextResponse {
    session_id: string;
    prediction: PredictionResult;
}

export interface InferenceStepResponse {
    session_id: string;
    step: number;
    real_extraction: number;
    predicted_action: number;
    predicted_action_desc: string;
    reward: number;
    capital_after: number;
}

const requireRecord = (value: unknown, label: string): Record<string, unknown> => {
    if (!isRecord(value)) {
        throw new Error(`${label} has an invalid response shape.`);
    }
    return value;
};

const requireString = (record: Record<string, unknown>, key: string): string => {
    const value = record[key];
    if (typeof value !== 'string' || !value.trim()) {
        throw new Error(`Inference response field ${key} is invalid.`);
    }
    return value;
};

const requireNumber = (record: Record<string, unknown>, key: string): number => {
    const value = record[key];
    if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new Error(`Inference response field ${key} is invalid.`);
    }
    return value;
};

const requireInteger = (record: Record<string, unknown>, key: string): number => {
    const value = requireNumber(record, key);
    if (!Number.isInteger(value)) {
        throw new Error(`Inference response field ${key} is invalid.`);
    }
    return value;
};

const optionalNumber = (
    record: Record<string, unknown>,
    key: string,
): number | undefined => {
    const value = record[key];
    if (value === undefined || value === null) {
        return undefined;
    }
    if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new Error(`Inference prediction field ${key} is invalid.`);
    }
    return value;
};

const normalizePrediction = (value: unknown): PredictionResult => {
    const payload = requireRecord(value, 'Inference prediction');
    const prediction: PredictionResult = {
        action: requireInteger(payload, 'action'),
        description: requireString(payload, 'description'),
    };
    const confidence = optionalNumber(payload, 'confidence');
    if (confidence !== undefined) {
        prediction.confidence = confidence;
    }
    const betStrategyId = optionalNumber(payload, 'bet_strategy_id');
    if (betStrategyId !== undefined) {
        prediction.betStrategyId = betStrategyId;
    }
    const betStrategyName = payload.bet_strategy_name;
    if (betStrategyName !== undefined && betStrategyName !== null) {
        if (typeof betStrategyName !== 'string') {
            throw new Error('Inference prediction field bet_strategy_name is invalid.');
        }
        prediction.betStrategyName = betStrategyName;
    }
    const suggestedBetAmount = optionalNumber(payload, 'suggested_bet_amount');
    if (suggestedBetAmount !== undefined) {
        prediction.suggestedBetAmount = suggestedBetAmount;
    }
    const currentBetAmount = optionalNumber(payload, 'current_bet_amount');
    if (currentBetAmount !== undefined) {
        prediction.currentBetAmount = currentBetAmount;
    }
    return prediction;
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
    return requireRecord(payload, 'API response');
};

const parseUploadResponse = (value: unknown): InferenceDatasetUploadResponse => {
    const payload = requireRecord(value, 'Dataset upload response');
    const rawDatasetId = payload.dataset_id;
    if (rawDatasetId !== null && parseDatasetId(rawDatasetId) === null) {
        throw new Error('Dataset upload response field dataset_id is invalid.');
    }
    const datasetName = payload.dataset_name;
    if (datasetName !== null && typeof datasetName !== 'string') {
        throw new Error('Dataset upload response field dataset_name is invalid.');
    }
    const datasetKind = payload.dataset_kind;
    if (datasetKind !== null && typeof datasetKind !== 'string') {
        throw new Error('Dataset upload response field dataset_kind is invalid.');
    }
    if (!Array.isArray(payload.columns) || payload.columns.some((column) => typeof column !== 'string')) {
        throw new Error('Dataset upload response field columns is invalid.');
    }
    return {
        dataset_id: rawDatasetId === null ? null : parseDatasetId(rawDatasetId),
        filename: requireString(payload, 'filename'),
        rows_imported: requireInteger(payload, 'rows_imported'),
        dataset_name: datasetName,
        dataset_kind: datasetKind,
        columns: payload.columns,
    };
};

const parseStartResponse = (value: unknown): InferenceStartResponse => {
    const payload = requireRecord(value, 'Inference start response');
    return {
        session_id: requireString(payload, 'session_id'),
        checkpoint: requireString(payload, 'checkpoint'),
        game_capital: requireNumber(payload, 'game_capital'),
        game_bet: requireNumber(payload, 'game_bet'),
        current_capital: requireNumber(payload, 'current_capital'),
        prediction: normalizePrediction(payload.prediction),
    };
};

const parseNextResponse = (value: unknown): InferenceNextResponse => {
    const payload = requireRecord(value, 'Inference prediction response');
    return {
        session_id: requireString(payload, 'session_id'),
        prediction: normalizePrediction(payload.prediction),
    };
};

const parseStepResponse = (value: unknown): InferenceStepResponse => {
    const payload = requireRecord(value, 'Inference step response');
    return {
        session_id: requireString(payload, 'session_id'),
        step: requireInteger(payload, 'step'),
        real_extraction: requireInteger(payload, 'real_extraction'),
        predicted_action: requireInteger(payload, 'predicted_action'),
        predicted_action_desc: requireString(payload, 'predicted_action_desc'),
        reward: requireInteger(payload, 'reward'),
        capital_after: requireInteger(payload, 'capital_after'),
    };
};

export const uploadInferenceDataset = async (
    file: File,
): Promise<InferenceDatasetUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const payload = await requestJson(
        '/api/data/upload?dataset_kind=inference',
        { method: 'POST', body: formData },
        'Upload failed.',
    );
    return parseUploadResponse(payload);
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
                checkpoint: options.checkpoint,
                dataset_id: options.datasetId,
                game_capital: options.gameCapital,
                game_bet: options.gameBet,
            }),
        },
        'Session start failed.',
    );
    return parseStartResponse(payload);
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
    return parseNextResponse(payload);
};

export const submitInferenceStep = async (
    sessionId: string,
    extraction: number,
): Promise<InferenceStepResponse> => {
    const payload = await requestJson(
        `/api/inference/sessions/${sessionId}/step`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ extraction }),
        },
        'Step failed.',
    );
    return parseStepResponse(payload);
};

export { normalizePrediction };
