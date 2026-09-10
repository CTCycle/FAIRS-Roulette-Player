import type {
    InferenceBetUpdateRequest,
    InferenceBetUpdateResponse,
    InferenceContextClearResponse,
    InferenceNextResponse as ApiInferenceNextResponse,
    InferenceRowsClearResponse,
    InferenceSessionStatusResponse as ApiInferenceSessionStatusResponse,
    InferenceSessionStepResponse,
    InferenceShutdownResponse,
    InferenceStartRequest,
    InferenceStartResponse as ApiInferenceStartResponse,
    InferenceStepRequest,
    InferenceStepResponse,
    PredictionResponse,
    UploadResponse,
} from '../generated/api';
import type { PredictionResult } from '../types/inference';
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

export type InferenceDatasetUploadResponse = UploadResponse;
export type InferenceStartResponse = Omit<ApiInferenceStartResponse, 'prediction'> & {
    prediction: PredictionResult;
};
export type InferenceNextResponse = Omit<ApiInferenceNextResponse, 'prediction'> & {
    prediction: PredictionResult;
};
export type { InferenceSessionStepResponse, InferenceStepResponse };
export type InferenceSessionStatusResponse = Omit<
    ApiInferenceSessionStatusResponse,
    'last_prediction'
> & {
    last_prediction: PredictionResult | null;
};

const normalizePrediction = (payload: PredictionResponse): PredictionResult => ({
    action: payload.action,
    description: payload.description,
    relativePreference: payload.relative_preference ?? undefined,
    betStrategyId: payload.bet_strategy_id ?? undefined,
    betStrategyName: payload.bet_strategy_name ?? undefined,
    suggestedBetAmount: payload.suggested_bet_amount ?? undefined,
    currentBetAmount: payload.current_bet_amount ?? undefined,
});

export const uploadInferenceDataset = async (
    file: File,
    signal?: AbortSignal,
): Promise<InferenceDatasetUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    return requestApiJson<UploadResponse>(
        '/api/data/upload?dataset_kind=inference',
        { method: 'POST', body: formData, signal },
        'Upload failed.',
    );
};

export const clearInferenceContext = async (
    signal?: AbortSignal,
): Promise<InferenceContextClearResponse> => (
    requestApiJson<InferenceContextClearResponse>(
        '/api/inference/context/clear',
        { method: 'POST', signal },
        'Unable to clear inference context.',
    )
);

export const startInferenceSession = async (
    options: InferenceSessionStartOptions,
    signal?: AbortSignal,
): Promise<InferenceStartResponse> => {
    const request: InferenceStartRequest = {
        checkpoint: options.checkpoint,
        dataset_id: options.datasetId,
        game_capital: options.gameCapital,
        game_bet: options.gameBet,
    };
    const payload = await requestApiJson<ApiInferenceStartResponse>(
        '/api/inference/sessions/start',
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(options.preserveSessionId
                    ? { 'X-Preserve-Inference-Session': options.preserveSessionId }
                    : {}),
            },
            body: JSON.stringify(request),
            signal,
        },
        'Session start failed.',
    );
    return {
        ...payload,
        prediction: normalizePrediction(payload.prediction),
    };
};

export const shutdownInferenceSession = async (
    sessionId: string,
    signal?: AbortSignal,
): Promise<InferenceShutdownResponse> => (
    requestApiJson<InferenceShutdownResponse>(
        `/api/inference/sessions/${sessionId}/shutdown`,
        { method: 'POST', signal },
        'Stop failed.',
    )
);

export const clearInferenceSessionRows = async (
    sessionId: string,
    signal?: AbortSignal,
): Promise<InferenceRowsClearResponse> => (
    requestApiJson<InferenceRowsClearResponse>(
        `/api/inference/sessions/${sessionId}/rows/clear`,
        { method: 'POST', signal },
        'Unable to clear session rows.',
    )
);

export const updateInferenceBet = async (
    sessionId: string,
    betAmount: number,
    signal?: AbortSignal,
): Promise<InferenceBetUpdateResponse> => {
    const request: InferenceBetUpdateRequest = { bet_amount: betAmount };
    return requestApiJson<InferenceBetUpdateResponse>(
        `/api/inference/sessions/${sessionId}/bet`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
            signal,
        },
        'Bet update failed.',
    );
};

export const requestNextInferencePrediction = async (
    sessionId: string,
    signal?: AbortSignal,
): Promise<InferenceNextResponse> => {
    const payload = await requestApiJson<ApiInferenceNextResponse>(
        `/api/inference/sessions/${sessionId}/next`,
        { method: 'POST', signal },
        'Prediction failed.',
    );
    return {
        ...payload,
        prediction: normalizePrediction(payload.prediction),
    };
};

export const submitInferenceStep = async (
    sessionId: string,
    extraction: number,
    signal?: AbortSignal,
): Promise<InferenceStepResponse> => {
    const request: InferenceStepRequest = { extraction };
    return requestApiJson<InferenceStepResponse>(
        `/api/inference/sessions/${sessionId}/step`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
            signal,
        },
        'Step failed.',
    );
};

export const getInferenceSession = async (
    sessionId: string,
    signal?: AbortSignal,
): Promise<InferenceSessionStatusResponse> => {
    const payload = await requestReadOnlyJson<ApiInferenceSessionStatusResponse>(
        `/api/inference/sessions/${sessionId}`,
        { signal },
        'Unable to recover inference session.',
    );
    return {
        ...payload,
        last_prediction: payload.last_prediction
            ? normalizePrediction(payload.last_prediction)
            : null,
    };
};

export { normalizePrediction };
