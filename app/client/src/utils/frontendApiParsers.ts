import type {
    DatasetSummaryResponse,
    TrainingCheckpointSummary,
} from '../generated/api';
import type {
    CheckpointOptionMetadata,
    DatasetSummaryItem,
} from '../types/frontendApi';

export const parseDatasetSummaryItems = (payload: unknown): DatasetSummaryItem[] => {
    const summary = payload as DatasetSummaryResponse;
    return summary.datasets.map((entry) => ({
        datasetId: entry.dataset_id,
        datasetName: entry.dataset_name,
        rowCount: entry.row_count,
    }));
};

export const parseCheckpointOptionMetadata = (
    summary: TrainingCheckpointSummary,
): CheckpointOptionMetadata => ({
    datasetId: summary.dataset_id ?? null,
    perceptiveFieldSize: summary.perceptive_field_size ?? null,
});
