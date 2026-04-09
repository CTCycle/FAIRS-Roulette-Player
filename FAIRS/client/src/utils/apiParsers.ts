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
    const normalizeMessage = (value: unknown): string | null => {
        if (typeof value === 'string') {
            const trimmed = value.trim();
            return trimmed.length > 0 ? trimmed : null;
        }

        if (Array.isArray(value)) {
            const parts = value
                .map((entry) => {
                    if (typeof entry === 'string') {
                        return normalizeMessage(entry);
                    }
                    if (!isRecord(entry)) {
                        return null;
                    }
                    const loc = Array.isArray(entry.loc)
                        ? entry.loc
                            .filter((segment): segment is string | number => (
                                typeof segment === 'string' || typeof segment === 'number'
                            ))
                            .join('.')
                        : '';
                    const message = normalizeMessage(entry.msg ?? entry.message ?? entry.detail);
                    if (!message) {
                        return null;
                    }
                    return loc ? `${loc}: ${message}` : message;
                })
                .filter((entry): entry is string => Boolean(entry));

            if (parts.length > 0) {
                return parts.join(' ');
            }
        }

        if (isRecord(value)) {
            return normalizeMessage(value.message ?? value.detail ?? value.msg ?? value.error);
        }

        return null;
    };

    const message = normalizeMessage(payload);
    return message ?? fallbackMessage;
};

