import type { TrainingCheckpointSummary } from '../generated/api';
import type { CheckpointOptionMetadata } from '../types/frontendApi';

export const parseCheckpointOptionMetadata = (
    summary: TrainingCheckpointSummary,
): CheckpointOptionMetadata => ({
    datasetId: summary.dataset_id ?? null,
    perceptiveFieldSize: summary.perceptive_field_size ?? null,
});
