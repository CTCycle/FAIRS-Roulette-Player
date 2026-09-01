import {
    parseCheckpointList,
    parseCheckpointMetadataResponse,
    parseDatasetSummaryItems,
} from './frontendApiParsers';
import type { CheckpointMetadataResponse, DatasetSummaryItem } from '../types/frontendApi';
import { requestReadOnlyJson } from './apiClient';

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
