import { useCallback, useEffect, useRef, useState } from 'react';
import { isRecord } from '../utils/apiParsers';
import { isAbortError, requestJson } from '../utils/apiClient';
import type {
    TrainingHistoryPoint,
    TrainingStats,
    TrainingStatusCode,
    TrainingStatusSnapshot,
} from '../types/training';

const TRAINING_STATUSES: ReadonlySet<TrainingStatusCode> = new Set([
    'idle',
    'exploration',
    'training',
    'completed',
    'error',
    'cancelled',
    'stopping',
]);

const DEFAULT_STATS: TrainingStats = {
    epoch: 0,
    total_epochs: 0,
    max_steps: 0,
    time_step: 0,
    loss: null,
    rmse: null,
    val_loss: null,
    val_rmse: null,
    reward: 0,
    val_reward: null,
    total_reward: 0,
    capital: 0,
    capital_gain: 0,
    current_bet_amount: null,
    current_strategy_id: null,
    epsilon: null,
    experience_count: 0,
    replay_buffer_size: 0,
    status: 'idle',
};

const DEFAULT_STATUS: TrainingStatusSnapshot = {
    job_id: null,
    is_training: false,
    latest_stats: DEFAULT_STATS,
    history: [],
    latest_env: {},
    poll_interval: 1,
};

const isFiniteNumber = (value: unknown): value is number => (
    typeof value === 'number' && Number.isFinite(value)
);

const requiredNumber = (
    record: Record<string, unknown>,
    key: string,
): number => {
    const value = record[key];
    if (!isFiniteNumber(value)) {
        throw new Error(`Training status field ${key} is invalid.`);
    }
    return value;
};

const requiredInteger = (
    record: Record<string, unknown>,
    key: string,
): number => {
    const value = requiredNumber(record, key);
    if (!Number.isInteger(value)) {
        throw new Error(`Training status field ${key} is invalid.`);
    }
    return value;
};

const nullableNumber = (
    record: Record<string, unknown>,
    key: string,
): number | null => {
    const value = record[key];
    if (value === null) {
        return null;
    }
    if (!isFiniteNumber(value)) {
        throw new Error(`Training status field ${key} is invalid.`);
    }
    return value;
};

const nullableInteger = (
    record: Record<string, unknown>,
    key: string,
): number | null => {
    const value = nullableNumber(record, key);
    if (value !== null && !Number.isInteger(value)) {
        throw new Error(`Training status field ${key} is invalid.`);
    }
    return value;
};

const parseHistoryPoint = (value: unknown): TrainingHistoryPoint => {
    if (!isRecord(value)) {
        throw new Error('Training history contains an invalid point.');
    }
    const point: TrainingHistoryPoint = {
        time_step: requiredInteger(value, 'time_step'),
        loss: requiredNumber(value, 'loss'),
        rmse: requiredNumber(value, 'rmse'),
        epoch: requiredInteger(value, 'epoch'),
    };
    for (const key of ['val_loss', 'val_rmse', 'val_reward', 'epsilon'] as const) {
        if (key in value) {
            point[key] = value[key] === null ? null : requiredNumber(value, key);
        }
    }
    for (const key of ['experience_count', 'replay_buffer_size'] as const) {
        if (key in value) {
            point[key] = requiredInteger(value, key);
        }
    }
    for (const key of ['reward', 'total_reward', 'capital', 'capital_gain'] as const) {
        if (key in value) {
            point[key] = requiredNumber(value, key);
        }
    }
    return point;
};

const parseTrainingStats = (value: unknown): TrainingStats => {
    if (!isRecord(value)) {
        throw new Error('Training status latest_stats is invalid.');
    }
    const status = value.status;
    if (typeof status !== 'string' || !TRAINING_STATUSES.has(status as TrainingStatusCode)) {
        throw new Error('Training status contains an invalid status code.');
    }
    const stats: TrainingStats = {
        epoch: requiredInteger(value, 'epoch'),
        total_epochs: requiredInteger(value, 'total_epochs'),
        max_steps: requiredInteger(value, 'max_steps'),
        time_step: requiredInteger(value, 'time_step'),
        loss: nullableNumber(value, 'loss'),
        rmse: nullableNumber(value, 'rmse'),
        val_loss: nullableNumber(value, 'val_loss'),
        val_rmse: nullableNumber(value, 'val_rmse'),
        reward: requiredNumber(value, 'reward'),
        val_reward: nullableNumber(value, 'val_reward'),
        total_reward: requiredNumber(value, 'total_reward'),
        capital: requiredNumber(value, 'capital'),
        capital_gain: requiredNumber(value, 'capital_gain'),
        current_bet_amount: nullableNumber(value, 'current_bet_amount'),
        current_strategy_id: nullableInteger(value, 'current_strategy_id'),
        epsilon: nullableNumber(value, 'epsilon'),
        experience_count: requiredInteger(value, 'experience_count'),
        replay_buffer_size: requiredInteger(value, 'replay_buffer_size'),
        status: status as TrainingStatusCode,
    };
    if ('current_strategy_name' in value) {
        if (typeof value.current_strategy_name !== 'string') {
            throw new Error('Training status field current_strategy_name is invalid.');
        }
        stats.current_strategy_name = value.current_strategy_name;
    }
    if ('message' in value) {
        if (typeof value.message !== 'string') {
            throw new Error('Training status field message is invalid.');
        }
        stats.message = value.message;
    }
    return stats;
};

export const parseTrainingStatus = (value: unknown): TrainingStatusSnapshot => {
    if (!isRecord(value)) {
        throw new Error('Training status response is invalid.');
    }
    const jobId = value.job_id;
    if (jobId !== null && typeof jobId !== 'string') {
        throw new Error('Training status field job_id is invalid.');
    }
    if (typeof value.is_training !== 'boolean') {
        throw new Error('Training status field is_training is invalid.');
    }
    if (!Array.isArray(value.history)) {
        throw new Error('Training status field history is invalid.');
    }
    if (!isRecord(value.latest_env)) {
        throw new Error('Training status field latest_env is invalid.');
    }
    const pollInterval = requiredNumber(value, 'poll_interval');
    if (pollInterval <= 0) {
        throw new Error('Training status field poll_interval is invalid.');
    }
    return {
        job_id: jobId,
        is_training: value.is_training,
        latest_stats: parseTrainingStats(value.latest_stats),
        history: value.history.map(parseHistoryPoint).slice(-2000),
        latest_env: value.latest_env,
        poll_interval: pollInterval,
    };
};

interface UseTrainingStatusResult {
    status: TrainingStatusSnapshot;
    isConnected: boolean;
    connectionError: string | null;
    isStopping: boolean;
    stopError: string | null;
    stopTraining: () => Promise<void>;
}

export const useTrainingStatus = (): UseTrainingStatusResult => {
    const [status, setStatus] = useState<TrainingStatusSnapshot>(DEFAULT_STATUS);
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState<string | null>(null);
    const [isStopping, setIsStopping] = useState(false);
    const [stopError, setStopError] = useState<string | null>(null);
    const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const pollIntervalRef = useRef(1000);
    const pollAbortRef = useRef<AbortController | null>(null);
    const reconnectAttemptRef = useRef(0);
    const mountedRef = useRef(true);
    const stopAbortRef = useRef<AbortController | null>(null);
    const stopInFlightRef = useRef(false);

    useEffect(() => {
        let cancelled = false;
        mountedRef.current = true;

        const pollStatus = async (): Promise<void> => {
            const startedAt = Date.now();
            try {
                pollAbortRef.current?.abort();
                const controller = new AbortController();
                pollAbortRef.current = controller;
                const parsed = parseTrainingStatus(await requestJson(
                    '/api/training/status',
                    { signal: controller.signal },
                    'Failed to fetch training status.',
                ));
                if (cancelled) {
                    return;
                }
                reconnectAttemptRef.current = 0;
                setStatus(parsed);
                setIsConnected(true);
                setConnectionError(null);
                pollIntervalRef.current = Math.max(250, parsed.poll_interval * 1000);
            } catch (error) {
                if (isAbortError(error)) {
                    return;
                }
                if (!cancelled) {
                    reconnectAttemptRef.current += 1;
                    setIsConnected(false);
                    setConnectionError(
                        error instanceof Error ? error.message : 'Failed to connect to training server',
                    );
                }
            } finally {
                if (!cancelled) {
                    const elapsed = Date.now() - startedAt;
                    const reconnectDelay = Math.min(
                        10_000,
                        1_000 * (2 ** Math.min(reconnectAttemptRef.current, 4)),
                    );
                    const delay = reconnectAttemptRef.current > 0
                        ? Math.max(0, reconnectDelay - elapsed)
                        : Math.max(0, pollIntervalRef.current - elapsed);
                    pollTimeoutRef.current = setTimeout(() => {
                        void pollStatus();
                    }, delay);
                }
            }
        };

        void pollStatus();
        return () => {
            cancelled = true;
            mountedRef.current = false;
            pollAbortRef.current?.abort();
            stopAbortRef.current?.abort();
            if (pollTimeoutRef.current !== null) {
                clearTimeout(pollTimeoutRef.current);
            }
        };
    }, []);

    const stopTraining = useCallback(async (): Promise<void> => {
        if (isStopping || stopInFlightRef.current) {
            return;
        }
        stopInFlightRef.current = true;
        setIsStopping(true);
        setStopError(null);
        const controller = new AbortController();
        stopAbortRef.current = controller;
        try {
            await requestJson(
                '/api/training/stop',
                { method: 'POST', signal: controller.signal },
                'Failed to stop training.',
            );
        } catch (error) {
            if (!isAbortError(error) && mountedRef.current) {
                setStopError(error instanceof Error ? error.message : 'Failed to stop training');
            }
        } finally {
            if (stopAbortRef.current === controller) {
                stopAbortRef.current = null;
            }
            stopInFlightRef.current = false;
            if (mountedRef.current) {
                setIsStopping(false);
            }
        }
    }, [isStopping]);

    return {
        status,
        isConnected,
        connectionError,
        isStopping,
        stopError,
        stopTraining,
    };
};
