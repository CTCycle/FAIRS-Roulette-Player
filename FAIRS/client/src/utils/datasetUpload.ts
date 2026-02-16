export type DatasetUploadStatus = 'idle' | 'uploading' | 'success' | 'error';

const DATASET_UPLOAD_ENDPOINT = '/api/data/upload?table=roulette_series';

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

export async function uploadDatasetFile(file: File): Promise<number> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(DATASET_UPLOAD_ENDPOINT, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const errorPayload = (await response.json().catch(() => null)) as { detail?: string } | null;
        const detail = errorPayload?.detail ?? `Upload failed (HTTP ${response.status}).`;
        throw new Error(detail);
    }

    const payload = (await response.json().catch(() => null)) as { rows_imported?: number } | null;
    return payload?.rows_imported ?? 0;
}
