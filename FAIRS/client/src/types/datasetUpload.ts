import type { DatasetUploadState } from '../context/AppStateContext';

export type DatasetUploadStateUpdates = Partial<
    Pick<DatasetUploadState, 'files' | 'uploadStatus' | 'uploadMessage'>
>;
