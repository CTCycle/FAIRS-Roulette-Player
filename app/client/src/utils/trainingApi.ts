import type {
    JobStartResponse,
    TrainingConfig as ApiTrainingConfig,
} from '../generated/api';
import type { CheckpointMetadataResponse, DatasetSummaryItem } from '../types/frontendApi';
import { requestJson, requestReadOnlyJson } from './apiClient';
import {
    parseCheckpointList,
    parseCheckpointMetadataResponse,
    parseDatasetSummaryItems,
} from './frontendApiParsers';

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
    payload: ApiTrainingConfig,
    signal?: AbortSignal,
): Promise<ApiTrainingConfig> => (
    requestJson(
        '/api/training/validate',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal,
        },
        'Training configuration is invalid.',
    ) as Promise<ApiTrainingConfig>
);

export const startTraining = async (
    payload: ApiTrainingConfig,
    signal?: AbortSignal,
): Promise<JobStartResponse> => (
    requestJson(
        '/api/training/start',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal,
        },
        'Unable to start training.',
    ) as Promise<JobStartResponse>
);
