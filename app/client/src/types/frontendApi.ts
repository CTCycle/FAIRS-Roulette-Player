export interface DatasetSummaryItem {
    datasetId: number;
    datasetName: string;
    rowCount: number | null;
}

export interface CheckpointMetadataResponse {
    checkpoint: string;
    summary: Record<string, unknown>;
}

export interface CheckpointOptionMetadata {
    datasetId: number | null;
    perceptiveFieldSize: number | null;
}

