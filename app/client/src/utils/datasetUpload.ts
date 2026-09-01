import { requestJson } from './apiClient';

export type DatasetUploadStatus = 'idle' | 'uploading' | 'success' | 'error';

const DATASET_UPLOAD_ENDPOINT = '/api/data/upload?dataset_kind=training';

const isObjectRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null
);

const extractImportedRows = (value: unknown): number => {
    if (!isObjectRecord(value)) {
        return 0;
    }
    return typeof value.rows_imported === 'number' ? value.rows_imported : 0;
};

export function formatFileSize(bytes: number): string {
    if (bytes === 0) {
        return '0 B';
    }
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export function isSupportedDatasetFile(file: File): boolean {
    const extension = file.name.split('.').pop()?.toLowerCase();
    return extension === 'csv' || extension === 'xlsx' || extension === 'xls';
}

export async function uploadDatasetFile(file: File, signal?: AbortSignal): Promise<number> {
    const formData = new FormData();
    formData.append('file', file);

    const payload = await requestJson(
        DATASET_UPLOAD_ENDPOINT,
        { method: 'POST', body: formData, signal },
        'Upload failed.',
    );
    return extractImportedRows(payload);
}
