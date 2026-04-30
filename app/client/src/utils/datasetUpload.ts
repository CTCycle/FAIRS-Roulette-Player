export type DatasetUploadStatus = 'idle' | 'uploading' | 'success' | 'error';

const DATASET_UPLOAD_ENDPOINT = '/api/data/upload?table=roulette_series';

const isObjectRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null
);

const extractErrorDetail = (value: unknown): string | null => {
    if (!isObjectRecord(value)) {
        return null;
    }
    return typeof value.detail === 'string' ? value.detail : null;
};

const extractImportedRows = (value: unknown): number => {
    if (!isObjectRecord(value)) {
        return 0;
    }
    return typeof value.rows_imported === 'number' ? value.rows_imported : 0;
};

const readJsonSafely = async (response: Response): Promise<unknown | null> => {
    try {
        return await response.json();
    } catch {
        return null;
    }
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

export async function uploadDatasetFile(file: File): Promise<number> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(DATASET_UPLOAD_ENDPOINT, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const errorPayload = await readJsonSafely(response);
        const detail = extractErrorDetail(errorPayload) ?? `Upload failed (HTTP ${response.status}).`;
        throw new Error(detail);
    }

    const payload = await readJsonSafely(response);
    return extractImportedRows(payload);
}
