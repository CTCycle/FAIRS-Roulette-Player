import {
    parseCheckpointList,
    parseCheckpointMetadataResponse,
    parseDatasetSummaryItems,
} from './frontendApiParsers';
import type { CheckpointMetadataResponse, DatasetSummaryItem } from '../types/frontendApi';
import { requestJson, requestReadOnlyJson } from './apiClient';

const getJson = async (endpoint: string, signal?: AbortSignal): Promise<unknown> => (
    requestReadOnlyJson(endpoint, { signal })
);

export const fetchTrainingCheckpoints = async (signal?: AbortSignal): Promise<string[]> => (
    parseCheckpointList(await getJson('/api/training/checkpoints', signal))
);

export const fetchTrainingDatasetSummaries = async (signal?: AbortSignal): Promise<DatasetSummaryItem[]> => (
    parseDatasetSummaryItems(await getJson('/api/datasets/training/summary', signal))
);

export const fetchCheckpointMetadata = async (
    checkpoint: string,
    signal?: AbortSignal,
): Promise<CheckpointMetadataResponse> => (
    parseCheckpointMetadataResponse(
        await getJson(
            `/api/training/checkpoints/${encodeURIComponent(checkpoint)}/metadata`,
            signal,
        ),
    )
);

export const validateTrainingPayload = async (
    payload: Record<string, unknown>,
    signal?: AbortSignal,
): Promise<Record<string, unknown>> => (
    requestJson(
        '/api/training/validate',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal,
        },
        'Training configuration is invalid.',
    ) as Promise<Record<string, unknown>>
);

export const startTraining = async (
    payload: Record<string, unknown>,
    signal?: AbortSignal,
): Promise<unknown> => (
    requestJson(
        '/api/training/start',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal,
        },
        'Unable to start training.',
    )
);
