import { isRecord, parseDatasetId } from './apiParsers';
import type {
    CheckpointMetadataResponse,
    CheckpointOptionMetadata,
    DatasetSummaryItem,
} from '../types/frontendApi';

const requireRecord = (value: unknown, label: string): Record<string, unknown> => {
    if (!isRecord(value)) {
        throw new Error(`${label} has an invalid shape.`);
    }
    return value;
};

const parseRowCount = (value: unknown): number | null => {
    if (value === null) {
        return null;
    }
    if (typeof value !== 'number' || !Number.isInteger(value) || value < 0) {
        throw new Error('Dataset summary row_count is invalid.');
    }
    return value;
};

const parseNullablePositiveInteger = (value: unknown, label: string): number | null => {
    if (value === null) {
        return null;
    }
    if (typeof value !== 'number' || !Number.isInteger(value) || value <= 0) {
        throw new Error(`${label} is invalid.`);
    }
    return value;
};

export const parseCheckpointList = (payload: unknown): string[] => {
    if (!Array.isArray(payload) || payload.some((entry) => typeof entry !== 'string')) {
        throw new Error('Checkpoint list has an invalid shape.');
    }
    return payload.map((entry) => {
        const checkpoint = entry.trim();
        if (!checkpoint) {
            throw new Error('Checkpoint list contains an empty checkpoint name.');
        }
        return checkpoint;
    });
};

export const parseDatasetSummaryItems = (payload: unknown): DatasetSummaryItem[] => {
    const root = requireRecord(payload, 'Dataset summary');
    if (!Array.isArray(root.datasets)) {
        throw new Error('Dataset summary datasets is invalid.');
    }

    return root.datasets.map((value) => {
        const entry = requireRecord(value, 'Dataset summary entry');
        const datasetId = parseDatasetId(entry.dataset_id);
        if (datasetId === null) {
            throw new Error('Dataset summary dataset_id is invalid.');
        }
        if (typeof entry.dataset_name !== 'string' || !entry.dataset_name.trim()) {
            throw new Error('Dataset summary dataset_name is invalid.');
        }
        return {
            datasetId,
            datasetName: entry.dataset_name,
            rowCount: parseRowCount(entry.row_count),
        };
    });
};

export const parseCheckpointMetadataResponse = (payload: unknown): CheckpointMetadataResponse => {
    const root = requireRecord(payload, 'Checkpoint metadata');
    if (typeof root.checkpoint !== 'string' || !root.checkpoint.trim()) {
        throw new Error('Checkpoint metadata checkpoint is invalid.');
    }
    return {
        checkpoint: root.checkpoint,
        summary: requireRecord(root.summary, 'Checkpoint metadata summary'),
    };
};

export const parseCheckpointOptionMetadata = (
    summary: Record<string, unknown>,
): CheckpointOptionMetadata => ({
    datasetId: parseNullablePositiveInteger(summary.dataset_id, 'Checkpoint metadata dataset_id'),
    perceptiveFieldSize: parseNullablePositiveInteger(
        summary.perceptive_field_size,
        'Checkpoint metadata perceptive_field_size',
    ),
});
