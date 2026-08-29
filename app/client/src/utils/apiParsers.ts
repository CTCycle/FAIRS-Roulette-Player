export const isRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null && !Array.isArray(value)
);

export const parseDatasetId = (value: unknown): number | null => {
    if (typeof value !== 'number' || !Number.isInteger(value) || value <= 0) {
        return null;
    }
    return value;
};

const parseFastApiDetail = (value: unknown): string | null => {
    if (typeof value === 'string') {
        const trimmed = value.trim();
        return trimmed.length > 0 ? trimmed : null;
    }
    if (!Array.isArray(value)) {
        return null;
    }

    const messages = value.map((entry) => {
        if (!isRecord(entry) || typeof entry.msg !== 'string') {
            return null;
        }
        const message = entry.msg.trim();
        if (!message) {
            return null;
        }
        if (!Array.isArray(entry.loc)) {
            return message;
        }
        const location = entry.loc
            .filter((segment): segment is string | number => (
                typeof segment === 'string' || typeof segment === 'number'
            ))
            .join('.');
        return location ? `${location}: ${message}` : message;
    }).filter((entry): entry is string => entry !== null);

    return messages.length > 0 ? messages.join(' ') : null;
};

export const parseApiErrorDetail = (payload: unknown, fallbackMessage: string): string => {
    if (!isRecord(payload)) {
        return fallbackMessage;
    }
    return parseFastApiDetail(payload.detail) ?? fallbackMessage;
};
