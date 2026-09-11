import { requestJson } from './apiClient';

export type DatasetUploadStatus = 'idle' | 'uploading' | 'success' | 'error';

const DATASET_UPLOAD_ENDPOINT = '/api/data/upload?dataset_kind=training';
const CSV_SEPARATOR_CANDIDATES = [',', ';', '\t', '|'] as const;

export const detectCsvSeparator = async (file: File): Promise<string> => {
    try {
        const sample = await file.slice(0, 64 * 1024).text();
        const lines = sample
            .split(/\r?\n/)
            .map((line) => line.trim())
            .filter(Boolean)
            .slice(0, 10);
        const scores = CSV_SEPARATOR_CANDIDATES.map((separator) => ({
            separator,
            score: lines.reduce(
                (total, line) => total + line.split(separator).length - 1,
                0,
            ),
        }));
        const detected = scores.reduce((best, current) => (
            current.score > best.score ? current : best
        ));
        return detected.score > 0 ? detected.separator : ',';
    } catch {
        return ',';
    }
};

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

    const endpoint = file.name.toLowerCase().endsWith('.csv')
        ? `${DATASET_UPLOAD_ENDPOINT}&csv_separator=${encodeURIComponent(await detectCsvSeparator(file))}`
        : DATASET_UPLOAD_ENDPOINT;

    const payload = await requestJson(
        endpoint,
        { method: 'POST', body: formData, signal },
        'Upload failed.',
    );
    return extractImportedRows(payload);
}
