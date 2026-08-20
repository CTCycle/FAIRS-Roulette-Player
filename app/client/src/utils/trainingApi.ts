import {
    parseCheckpointList,
    parseCheckpointMetadataResponse,
    parseDatasetSummaryItems,
} from './frontendApiParsers';
import type { CheckpointMetadataResponse, DatasetSummaryItem } from '../types/frontendApi';

const getJson = async (endpoint: string): Promise<unknown> => {
    const response = await fetch(endpoint);
    if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
    }
    return response.json();
};

export const fetchTrainingCheckpoints = async (): Promise<string[]> => (
    parseCheckpointList(await getJson('/api/training/checkpoints'))
);

export const fetchTrainingDatasetSummaries = async (): Promise<DatasetSummaryItem[]> => (
    parseDatasetSummaryItems(await getJson('/api/datasets/training/summary'))
);

export const fetchCheckpointMetadata = async (
    checkpoint: string,
): Promise<CheckpointMetadataResponse> => (
    parseCheckpointMetadataResponse(
        await getJson(`/api/training/checkpoints/${encodeURIComponent(checkpoint)}/metadata`),
    )
);
