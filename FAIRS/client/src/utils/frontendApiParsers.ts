import { isRecord, parseDatasetId } from './apiParsers';
import type {
    CheckpointMetadataResponse,
    CheckpointOptionMetadata,
    DatasetSummaryItem,
} from '../types/frontendApi';

const parseRowCount = (value: unknown): number | null => {
    if (typeof value === 'number' && Number.isFinite(value)) {
        return value;
    }
    return null;
};

const parsePositiveInteger = (value: unknown): number | null => {
    if (typeof value !== 'number' || !Number.isInteger(value) || value <= 0) {
        return null;
    }
    return value;
};

export const parseCheckpointList = (payload: unknown): string[] => {
    if (!Array.isArray(payload)) {
        return [];
    }

    return payload.flatMap((entry) => {
        if (typeof entry === 'string') {
            const trimmed = entry.trim();
            return trimmed.length > 0 ? [trimmed] : [];
        }
        if (typeof entry === 'number' && Number.isFinite(entry)) {
            return [String(entry)];
        }
        return [];
    });
};

export const parseDatasetSummaryItems = (payload: unknown): DatasetSummaryItem[] => {
    const datasets = isRecord(payload) ? payload.datasets : undefined;
    if (!Array.isArray(datasets)) {
        return [];
    }

    return datasets
        .filter((entry): entry is Record<string, unknown> => isRecord(entry))
        .map((entry) => ({
            datasetId: parseDatasetId(entry.dataset_id),
            datasetName: typeof entry.dataset_name === 'string' ? entry.dataset_name : '',
            rowCount: parseRowCount(entry.row_count),
        }))
        .filter((entry) => entry.datasetId.length > 0);
};

export const parseCheckpointMetadataResponse = (payload: unknown): CheckpointMetadataResponse => {
    const safePayload = isRecord(payload) ? payload : {};
    const checkpoint = typeof safePayload.checkpoint === 'string'
        ? safePayload.checkpoint
        : '';
    const summary = isRecord(safePayload.summary)
        ? safePayload.summary
        : {};

    return {
        checkpoint,
        summary,
    };
};

export const parseCheckpointOptionMetadata = (
    summary: Record<string, unknown>,
): CheckpointOptionMetadata => ({
    datasetId: parseDatasetId(summary.dataset_id),
    perceptiveFieldSize: parsePositiveInteger(summary.perceptive_field_size),
});

