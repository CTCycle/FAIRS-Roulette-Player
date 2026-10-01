// Copyright © 2023 Thomas Virdis
// Licensed under the MIT License.

import type { TrainingCheckpointMetadataResponse } from '../generated/api';

export interface DatasetSummaryItem {
    datasetId: number;
    datasetName: string;
    rowCount: number;
}

export type CheckpointMetadataResponse = TrainingCheckpointMetadataResponse;

export interface CheckpointOptionMetadata {
    datasetId: number | null;
    perceptiveFieldSize: number | null;
}
