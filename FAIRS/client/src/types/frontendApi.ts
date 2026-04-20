export interface DatasetSummaryItem {
    datasetId: string;
    datasetName: string;
    rowCount: number | null;
}

export interface CheckpointMetadataResponse {
    checkpoint: string;
    summary: Record<string, unknown>;
}

export interface CheckpointOptionMetadata {
    datasetId: string;
    perceptiveFieldSize: number | null;
}

