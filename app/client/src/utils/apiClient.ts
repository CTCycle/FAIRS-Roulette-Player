import { parseApiErrorDetail } from './apiParsers';

export class ApiRequestError extends Error {
    readonly status: number;
    readonly payload: unknown;

    constructor(message: string, status: number, payload: unknown) {
        super(message);
        this.name = 'ApiRequestError';
        this.status = status;
        this.payload = payload;
    }
}

export const isAbortError = (error: unknown): boolean => (
    (error instanceof DOMException && error.name === 'AbortError')
    || (error instanceof Error && error.name === 'AbortError')
);

const readJson = async (response: Response): Promise<unknown> => (
    response.json().catch(() => null)
);

export const requestJson = async (
    endpoint: string,
    init: RequestInit = {},
    fallbackMessage = 'Request failed.',
): Promise<unknown> => {
    const response = await fetch(endpoint, init);
    const payload = await readJson(response);
    if (!response.ok) {
        throw new ApiRequestError(
            parseApiErrorDetail(payload, fallbackMessage),
            response.status,
            payload,
        );
    }
    return payload;
};

const READ_ONLY_MAX_ATTEMPTS = 6;
const READ_ONLY_BASE_DELAY_MS = 500;
const READ_ONLY_MAX_DELAY_MS = 10_000;

const isRetryableReadError = (error: unknown): boolean => {
    if (!(error instanceof ApiRequestError)) {
        return true;
    }
    return error.status === 408
        || error.status === 425
        || error.status === 429
        || error.status >= 500;
};

const createAbortError = (): Error => {
    if (typeof DOMException !== 'undefined') {
        return new DOMException('The request was aborted.', 'AbortError');
    }
    const error = new Error('The request was aborted.');
    error.name = 'AbortError';
    return error;
};

const waitForReadinessRetry = (
    delayMs: number,
    signal?: AbortSignal,
): Promise<void> => new Promise((resolve, reject) => {
    if (signal?.aborted) {
        reject(createAbortError());
        return;
    }

    const cleanup = () => signal?.removeEventListener('abort', onAbort);
    const finish = () => {
        cleanup();
        resolve();
    };
    const onAbort = () => {
        clearTimeout(timer);
        cleanup();
        reject(createAbortError());
    };

    const timer = setTimeout(finish, delayMs);
    signal?.addEventListener('abort', onAbort, { once: true });
});

/**
 * Retry only idempotent GET requests while a local backend becomes ready.
 * Callers must use requestJson directly for mutations so retries never repeat
 * a state-changing operation.
 */
export const requestReadOnlyJson = async (
    endpoint: string,
    init: RequestInit = {},
    fallbackMessage = 'Request failed.',
): Promise<unknown> => {
    const method = (init.method ?? 'GET').toUpperCase();
    if (method !== 'GET') {
        throw new Error('Read-only requests must use GET.');
    }

    const signal = init.signal ?? undefined;
    for (let attempt = 0; attempt < READ_ONLY_MAX_ATTEMPTS; attempt += 1) {
        try {
            return await requestJson(endpoint, init, fallbackMessage);
        } catch (error) {
            const isLastAttempt = attempt === READ_ONLY_MAX_ATTEMPTS - 1;
            if (isLastAttempt || isAbortError(error) || !isRetryableReadError(error)) {
                throw error;
            }
            const delayMs = Math.min(
                READ_ONLY_MAX_DELAY_MS,
                READ_ONLY_BASE_DELAY_MS * (2 ** attempt),
            );
            await waitForReadinessRetry(delayMs, signal);
        }
    }

    throw new Error(fallbackMessage);
};
