import type { PredictionResult } from '../types/inference';
import { isRecord, parseDatasetId } from './apiParsers';
import {
    requestJson as requestApiJson,
    requestReadOnlyJson,
} from './apiClient';

export interface InferenceSessionStartOptions {
    checkpoint: string;
    datasetId: number;
    gameCapital: number;
    gameBet: number;
    preserveSessionId?: string;
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

export interface InferenceSessionStepResponse {
    step: number;
    bet_amount: number;
    predicted_action: number;
    predicted_action_desc: string;
    predicted_confidence: number | null;
    observed_outcome_id: number | null;
    reward: number | null;
    capital_after: number;
}

export interface InferenceSessionStatusResponse {
    session_id: string;
    checkpoint: string;
    dataset_id: number;
    initial_capital: number;
    current_capital: number;
    current_bet: number;
    step_count: number;
    prediction_pending: boolean;
    last_prediction: PredictionResult | null;
    steps: InferenceSessionStepResponse[];
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

const optionalInteger = (
    record: Record<string, unknown>,
    key: string,
): number | undefined => {
    const value = optionalNumber(record, key);
    if (value !== undefined && !Number.isInteger(value)) {
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
    const relativePreference = optionalNumber(payload, 'confidence');
    if (relativePreference !== undefined && (relativePreference < 0 || relativePreference > 1)) {
        throw new Error('Inference prediction field confidence is invalid.');
    }
    if (relativePreference !== undefined) {
        prediction.relativePreference = relativePreference;
    }
    const betStrategyId = optionalInteger(payload, 'bet_strategy_id');
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
    const suggestedBetAmount = optionalInteger(payload, 'suggested_bet_amount');
    if (suggestedBetAmount !== undefined) {
        prediction.suggestedBetAmount = suggestedBetAmount;
    }
    const currentBetAmount = optionalInteger(payload, 'current_bet_amount');
    if (currentBetAmount !== undefined) {
        prediction.currentBetAmount = currentBetAmount;
    }
    return prediction;
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

const nullableInteger = (
    record: Record<string, unknown>,
    key: string,
): number | null => {
    const value = record[key];
    if (value === null) {
        return null;
    }
    return requireInteger(record, key);
};

const parseStartResponse = (value: unknown): InferenceStartResponse => {
    const payload = requireRecord(value, 'Inference start response');
    return {
        session_id: requireString(payload, 'session_id'),
        checkpoint: requireString(payload, 'checkpoint'),
        game_capital: requireInteger(payload, 'game_capital'),
        game_bet: requireInteger(payload, 'game_bet'),
        current_capital: requireInteger(payload, 'current_capital'),
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

const parseSessionStatusResponse = (value: unknown): InferenceSessionStatusResponse => {
    const payload = requireRecord(value, 'Inference session response');
    const rawSteps = payload.steps;
    if (!Array.isArray(rawSteps)) {
        throw new Error('Inference session steps are invalid.');
    }
    const steps = rawSteps.map((rawStep) => {
        const step = requireRecord(rawStep, 'Inference session step');
        return {
            step: requireInteger(step, 'step'),
            bet_amount: requireInteger(step, 'bet_amount'),
            predicted_action: requireInteger(step, 'predicted_action'),
            predicted_action_desc: requireString(step, 'predicted_action_desc'),
            predicted_confidence: step.predicted_confidence === null
                ? null
                : optionalNumber(step, 'predicted_confidence') ?? null,
            observed_outcome_id: nullableInteger(step, 'observed_outcome_id'),
            reward: nullableInteger(step, 'reward'),
            capital_after: requireInteger(step, 'capital_after'),
        };
    });
    const rawPrediction = payload.last_prediction;
    return {
        session_id: requireString(payload, 'session_id'),
        checkpoint: requireString(payload, 'checkpoint'),
        dataset_id: requireInteger(payload, 'dataset_id'),
        initial_capital: requireInteger(payload, 'initial_capital'),
        current_capital: requireInteger(payload, 'current_capital'),
        current_bet: requireInteger(payload, 'current_bet'),
        step_count: requireInteger(payload, 'step_count'),
        prediction_pending: payload.prediction_pending === true,
        last_prediction: rawPrediction === null
            ? null
            : normalizePrediction(rawPrediction),
        steps,
    };
};

export const uploadInferenceDataset = async (
    file: File,
    signal?: AbortSignal,
): Promise<InferenceDatasetUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const payload = await requestApiJson(
        '/api/data/upload?dataset_kind=inference',
        { method: 'POST', body: formData, signal },
        'Upload failed.',
    );
    return parseUploadResponse(payload);
};

export const clearInferenceContext = async (signal?: AbortSignal): Promise<Record<string, unknown>> => (
    requireRecord(
        await requestApiJson(
            '/api/inference/context/clear',
            { method: 'POST', signal },
            'Unable to clear inference context.',
        ),
        'API response',
    )
);

export const startInferenceSession = async (
    options: InferenceSessionStartOptions,
    signal?: AbortSignal,
): Promise<InferenceStartResponse> => {
    const payload = await requestApiJson(
        '/api/inference/sessions/start',
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(options.preserveSessionId
                    ? { 'X-Preserve-Inference-Session': options.preserveSessionId }
                    : {}),
            },
            body: JSON.stringify({
                checkpoint: options.checkpoint,
                dataset_id: options.datasetId,
                game_capital: options.gameCapital,
                game_bet: options.gameBet,
            }),
            signal,
        },
        'Session start failed.',
    );
    return parseStartResponse(payload);
};

export const shutdownInferenceSession = async (
    sessionId: string,
    signal?: AbortSignal,
): Promise<Record<string, unknown>> => (
    requireRecord(
        await requestApiJson(
        `/api/inference/sessions/${sessionId}/shutdown`,
        { method: 'POST', signal },
        'Stop failed.',
        ),
        'API response',
    )
);

export const clearInferenceSessionRows = async (
    sessionId: string,
    signal?: AbortSignal,
): Promise<Record<string, unknown>> => (
    requireRecord(
        await requestApiJson(
        `/api/inference/sessions/${sessionId}/rows/clear`,
        { method: 'POST', signal },
        'Unable to clear session rows.',
        ),
        'API response',
    )
);

export const updateInferenceBet = async (
    sessionId: string,
    betAmount: number,
    signal?: AbortSignal,
): Promise<Record<string, unknown>> => (
    requireRecord(
        await requestApiJson(
        `/api/inference/sessions/${sessionId}/bet`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bet_amount: betAmount }),
            signal,
        },
        'Bet update failed.',
        ),
        'API response',
    )
);

export const requestNextInferencePrediction = async (
    sessionId: string,
    signal?: AbortSignal,
): Promise<InferenceNextResponse> => {
    const payload = await requestApiJson(
        `/api/inference/sessions/${sessionId}/next`,
        { method: 'POST', signal },
        'Prediction failed.',
    );
    return parseNextResponse(payload);
};

export const submitInferenceStep = async (
    sessionId: string,
    extraction: number,
    signal?: AbortSignal,
): Promise<InferenceStepResponse> => {
    const payload = await requestApiJson(
        `/api/inference/sessions/${sessionId}/step`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ extraction }),
            signal,
        },
        'Step failed.',
    );
    return parseStepResponse(payload);
};

export const getInferenceSession = async (
    sessionId: string,
    signal?: AbortSignal,
): Promise<InferenceSessionStatusResponse> => {
    const payload = await requestReadOnlyJson(
        `/api/inference/sessions/${sessionId}`,
        { signal },
        'Unable to recover inference session.',
    );
    return parseSessionStatusResponse(payload);
};

export { normalizePrediction };
