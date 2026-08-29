import type { DatasetUploadStatus } from '../utils/datasetUpload';

export interface FileMetadata {
    name: string;
    size: number;
    type: string;
}

export interface DatasetUploadState {
    files: FileMetadata[];
    uploadStatus: DatasetUploadStatus;
    uploadMessage: string;
}

export type DatasetUploadStateUpdates = Partial<
    Pick<DatasetUploadState, 'files' | 'uploadStatus' | 'uploadMessage'>
>;
