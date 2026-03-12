export const isRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null
);

export const parseDatasetId = (value: unknown): string => {
    if (typeof value === 'number' && Number.isInteger(value) && value > 0) {
        return String(value);
    }
    if (typeof value === 'string') {
        const trimmed = value.trim();
        if (/^\d+$/.test(trimmed)) {
            return trimmed;
        }
    }
    return '';
};

export const parseApiErrorDetail = (payload: unknown, fallbackMessage: string): string => {
    if (!isRecord(payload)) {
        return fallbackMessage;
    }
    const detail = payload.detail;
    if (typeof detail !== 'string') {
        return fallbackMessage;
    }
    const trimmed = detail.trim();
    return trimmed.length > 0 ? trimmed : fallbackMessage;
};

