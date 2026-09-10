import type {
    DatasetSummaryResponse,
    JobStartResponse,
    TrainingCheckpointListResponse,
    TrainingCheckpointMetadataResponse,
    TrainingConfig as ApiTrainingConfig,
} from '../generated/api';
import type { CheckpointMetadataResponse, DatasetSummaryItem } from '../types/frontendApi';
import { requestJson, requestReadOnlyJson } from './apiClient';

export const fetchTrainingCheckpoints = async (
    signal?: AbortSignal,
): Promise<TrainingCheckpointListResponse> => (
    requestReadOnlyJson<TrainingCheckpointListResponse>(
        '/api/training/checkpoints',
        { signal },
    )
);

export const fetchTrainingDatasetSummaries = async (
    signal?: AbortSignal,
): Promise<DatasetSummaryItem[]> => {
    const payload = await requestReadOnlyJson<DatasetSummaryResponse>(
        '/api/datasets/training/summary',
        { signal },
    );
    return payload.datasets.map((entry) => ({
        datasetId: entry.dataset_id,
        datasetName: entry.dataset_name,
        rowCount: entry.row_count,
    }));
};

export const fetchCheckpointMetadata = async (
    checkpoint: string,
    signal?: AbortSignal,
): Promise<CheckpointMetadataResponse> => (
    requestReadOnlyJson<TrainingCheckpointMetadataResponse>(
        `/api/training/checkpoints/${encodeURIComponent(checkpoint)}/metadata`,
        { signal },
    )
);

export const validateTrainingPayload = async (
    payload: ApiTrainingConfig,
    signal?: AbortSignal,
): Promise<ApiTrainingConfig> => (
    requestJson<ApiTrainingConfig>(
        '/api/training/validate',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal,
        },
        'Training configuration is invalid.',
    )
);

export const startTraining = async (
    payload: ApiTrainingConfig,
    signal?: AbortSignal,
): Promise<JobStartResponse> => (
    requestJson<JobStartResponse>(
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
