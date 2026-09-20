import { useCallback, useEffect, useState } from 'react';
import type { HealthResponse } from '../generated/api';
import type { BackendStartupState } from '../types/startup';
import {
    isAbortError,
    requestReadOnlyJson,
} from '../utils/apiClient';

const STARTUP_TIMEOUT_MS = 60_000;
const HEALTH_REQUEST_TIMEOUT_MS = 2_500;
const HEALTH_POLL_INTERVAL_MS = 1_000;

const waitForNextPoll = (delayMs: number, signal: AbortSignal): Promise<void> => (
    new Promise((resolve) => {
        if (signal.aborted) {
            resolve();
            return;
        }

        const onAbort = () => {
            window.clearTimeout(timer);
            signal.removeEventListener('abort', onAbort);
            resolve();
        };
        const timer = window.setTimeout(() => {
            signal.removeEventListener('abort', onAbort);
            resolve();
        }, delayMs);
        signal.addEventListener('abort', onAbort, { once: true });
    })
);

const readHealthWithTimeout = async (
    signal: AbortSignal,
    timeoutMs: number,
): Promise<HealthResponse> => {
    const requestController = new AbortController();
    const forwardAbort = () => requestController.abort();
    if (signal.aborted) {
        requestController.abort();
    } else {
        signal.addEventListener('abort', forwardAbort, { once: true });
    }

    const timeout = window.setTimeout(
        () => requestController.abort(),
        timeoutMs,
    );

    try {
        return await requestReadOnlyJson<HealthResponse>(
            '/api/health',
            { signal: requestController.signal },
            'The FAIRS backend is not ready yet.',
        );
    } finally {
        window.clearTimeout(timeout);
        signal.removeEventListener('abort', forwardAbort);
    }
};

const isHealthy = (health: HealthResponse): boolean => (
    health.status === 'ok' && health.application === 'FAIRS'
);

export const useBackendStartup = (): BackendStartupState & { retry: () => void } => {
    const [attempt, setAttempt] = useState(0);
    const [status, setStatus] = useState<BackendStartupState['status']>('waiting');
    const [elapsedSeconds, setElapsedSeconds] = useState(0);

    const retry = useCallback(() => {
        setStatus('waiting');
        setElapsedSeconds(0);
        setAttempt((currentAttempt) => currentAttempt + 1);
    }, []);

    useEffect(() => {
        const controller = new AbortController();
        const startedAt = Date.now();
        let mounted = true;

        const updateElapsed = () => {
            if (mounted) {
                setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
            }
        };

        const progressTimer = window.setInterval(updateElapsed, 1_000);

        const pollUntilReady = async () => {
            const deadline = startedAt + STARTUP_TIMEOUT_MS;

            while (!controller.signal.aborted && Date.now() < deadline) {
                updateElapsed();
                try {
                    const remainingMs = deadline - Date.now();
                    const health = await readHealthWithTimeout(
                        controller.signal,
                        Math.min(HEALTH_REQUEST_TIMEOUT_MS, remainingMs),
                    );
                    if (isHealthy(health)) {
                        if (mounted) {
                            setStatus('ready');
                        }
                        return;
                    }
                } catch (error) {
                    if (controller.signal.aborted || (isAbortError(error) && !mounted)) {
                        return;
                    }
                    // Connection failures are expected while the local backend starts.
                }

                const remainingMs = deadline - Date.now();
                if (remainingMs > 0) {
                    await waitForNextPoll(
                        Math.min(HEALTH_POLL_INTERVAL_MS, remainingMs),
                        controller.signal,
                    );
                }
            }

            if (mounted && !controller.signal.aborted) {
                setStatus('error');
            }
        };

        void pollUntilReady();

        return () => {
            mounted = false;
            controller.abort();
            window.clearInterval(progressTimer);
        };
    }, [attempt]);

    return { status, elapsedSeconds, retry };
};
