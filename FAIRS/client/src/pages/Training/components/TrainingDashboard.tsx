import React, { useMemo, useState, useEffect, useRef, useId } from 'react';
import { Activity, ArrowUpRight, TrendingUp, DollarSign, Target, Clock, AlertCircle } from 'lucide-react';

import { TrainingLossChart, type TrainingHistoryPoint } from './TrainingLossChart';
import { TrainingMetricsChart } from './TrainingMetricsChart';

interface TrainingStats {
    epoch: number;
    total_epochs: number;
    max_steps?: number;
    time_step: number;
    loss: number | null;
    rmse: number | null;
    val_loss: number | null;
    val_rmse: number | null;
    reward: number;
    val_reward: number | null;
    total_reward: number;
    capital: number;
    capital_gain: number;
    current_bet_amount?: number | null;
    current_strategy_id?: number | null;
    current_strategy_name?: string;
    status: 'idle' | 'exploration' | 'training' | 'completed' | 'error' | 'cancelled';
    message?: string;
}

interface TrainingStatusResponse {
    job_id?: string | null;
    is_training: boolean;
    latest_stats: TrainingStats;
    history?: TrainingHistoryPoint[];
    poll_interval?: number;
}

interface TrainingDashboardProps {
    isActive: boolean;
    onTrainingStart?: () => void;
    onTrainingEnd?: () => void;
}

export const TrainingDashboard: React.FC<TrainingDashboardProps> = ({ isActive, onTrainingStart, onTrainingEnd }) => {
    const defaultStats: TrainingStats = {
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
        current_strategy_name: undefined,
        status: 'idle',
    };
    const [stats, setStats] = useState<TrainingStats>(defaultStats);
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState<string | null>(null);
    const [historyPoints, setHistoryPoints] = useState<TrainingHistoryPoint[]>([]);
    const [isStopping, setIsStopping] = useState(false);
    const [stopRequested, setStopRequested] = useState(false);
    const [stopError, setStopError] = useState<string | null>(null);
    const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const pollIntervalRef = useRef(1000);
    const backendActiveRef = useRef(false);
    const onTrainingStartRef = useRef(onTrainingStart);
    const onTrainingEndRef = useRef(onTrainingEnd);
    const pollAbortRef = useRef<AbortController | null>(null);
    const statsRef = useRef(defaultStats);
    const jobIdRef = useRef<string | null>(null);

    const maxHistoryPoints = 2000;
    const trainingEndStatuses: TrainingStats['status'][] = ['completed', 'error', 'cancelled'];
    const validStatus = (value: unknown): value is TrainingStats['status'] => (
        typeof value === 'string'
        && (
            trainingEndStatuses.includes(value as TrainingStats['status'])
            || value === 'idle'
            || value === 'exploration'
            || value === 'training'
        )
    );
    const toFiniteNumber = (value: unknown, fallback: number) => {
        const numeric = typeof value === 'number' ? value : Number(value);
        return Number.isFinite(numeric) ? numeric : fallback;
    };
    const toFiniteNumberOrNull = (value: unknown): number | null => {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        const numeric = typeof value === 'number' ? value : Number(value);
        return Number.isFinite(numeric) ? numeric : null;
    };
    const normalizeOptionalMetric = (
        candidate: Partial<TrainingStats>,
        key: 'loss' | 'rmse' | 'val_loss' | 'val_rmse' | 'val_reward',
        fallback: number | null,
    ): number | null => {
        if (!Object.prototype.hasOwnProperty.call(candidate, key)) {
            return fallback;
        }
        return toFiniteNumberOrNull(candidate[key]);
    };
    const normalizeStats = (value: unknown, fallback: TrainingStats): TrainingStats | null => {
        if (!value || typeof value !== 'object') {
            return null;
        }
        const candidate = value as Partial<TrainingStats>;
        return {
            ...fallback,
            ...candidate,
            epoch: toFiniteNumber(candidate.epoch, fallback.epoch),
            total_epochs: toFiniteNumber(candidate.total_epochs, fallback.total_epochs),
            max_steps: candidate.max_steps === undefined ? fallback.max_steps : toFiniteNumber(candidate.max_steps, fallback.max_steps ?? 0),
            time_step: toFiniteNumber(candidate.time_step, fallback.time_step),
            loss: normalizeOptionalMetric(candidate, 'loss', fallback.loss),
            rmse: normalizeOptionalMetric(candidate, 'rmse', fallback.rmse),
            val_loss: normalizeOptionalMetric(candidate, 'val_loss', fallback.val_loss),
            val_rmse: normalizeOptionalMetric(candidate, 'val_rmse', fallback.val_rmse),
            reward: toFiniteNumber(candidate.reward, fallback.reward),
            val_reward: normalizeOptionalMetric(candidate, 'val_reward', fallback.val_reward),
            total_reward: toFiniteNumber(candidate.total_reward, fallback.total_reward),
            capital: toFiniteNumber(candidate.capital, fallback.capital),
            capital_gain: toFiniteNumber(candidate.capital_gain, fallback.capital_gain),
            current_bet_amount: candidate.current_bet_amount === undefined
                ? fallback.current_bet_amount
                : toFiniteNumberOrNull(candidate.current_bet_amount),
            current_strategy_id: candidate.current_strategy_id === undefined
                ? fallback.current_strategy_id
                : toFiniteNumberOrNull(candidate.current_strategy_id),
            current_strategy_name: typeof candidate.current_strategy_name === 'string'
                ? candidate.current_strategy_name
                : fallback.current_strategy_name,
            status: validStatus(candidate.status) ? candidate.status : fallback.status,
            message: typeof candidate.message === 'string' ? candidate.message : fallback.message,
        };
    };
    const isHistoryPoint = (point: unknown): point is TrainingHistoryPoint => {
        if (!point || typeof point !== 'object') {
            return false;
        }
        const candidate = point as TrainingHistoryPoint;
        return Number.isFinite(candidate.time_step)
            && Number.isFinite(candidate.epoch)
            && Number.isFinite(candidate.loss)
            && Number.isFinite(candidate.rmse);
    };

    useEffect(() => {
        onTrainingStartRef.current = onTrainingStart;
    }, [onTrainingStart]);

    useEffect(() => {
        onTrainingEndRef.current = onTrainingEnd;
    }, [onTrainingEnd]);

    useEffect(() => {
        statsRef.current = stats;
    }, [stats]);

    useEffect(() => {
        if (isActive) {
            setStopRequested(false);
            setStopError(null);
        }
    }, [isActive]);

    useEffect(() => {
        let cancelled = false;

        const pollStatus = async () => {
            const pollStartTime = Date.now();
            let trainingEnded = false;
            try {
                pollAbortRef.current?.abort();
                const controller = new AbortController();
                pollAbortRef.current = controller;

                const response = await fetch('/api/training/status', {
                    signal: controller.signal,
                });
                if (!response.ok) {
                    throw new Error(`Failed to fetch training status (${response.status})`);
                }
                const payload = (await response.json()) as TrainingStatusResponse;
                setIsConnected(true);
                setConnectionError(null);

                const responseJobId = typeof payload.job_id === 'string' && payload.job_id.length > 0
                    ? payload.job_id
                    : null;
                if (responseJobId && responseJobId !== jobIdRef.current) {
                    jobIdRef.current = responseJobId;
                    setStopRequested(false);
                    setStopError(null);
                    setHistoryPoints([]);
                }

                const backendActive = Boolean(payload.is_training);
                let endedFromBackend = false;
                if (backendActive && !backendActiveRef.current) {
                    backendActiveRef.current = true;
                    onTrainingStartRef.current?.();
                } else if (!backendActive && backendActiveRef.current) {
                    backendActiveRef.current = false;
                    endedFromBackend = true;
                }

                const normalizedStats = normalizeStats(payload.latest_stats, statsRef.current);
                if (normalizedStats) {
                    setStats(normalizedStats);
                    const endedFromStatus = trainingEndStatuses.includes(normalizedStats.status);
                    if (endedFromStatus) {
                        backendActiveRef.current = false;
                    }
                    trainingEnded = endedFromBackend || endedFromStatus;
                } else {
                    trainingEnded = endedFromBackend;
                }

                if (trainingEnded) {
                    onTrainingEndRef.current?.();
                }

                if (Array.isArray(payload.history)) {
                    const trimmedHistory = payload.history.slice(-maxHistoryPoints);
                    const filteredHistory = trimmedHistory.filter(isHistoryPoint);
                    setHistoryPoints(filteredHistory);
                }

                if (typeof payload.poll_interval === 'number' && payload.poll_interval > 0) {
                    pollIntervalRef.current = Math.max(250, payload.poll_interval * 1000);
                }
            } catch (err) {
                if (err instanceof DOMException && err.name === 'AbortError') {
                    return;
                }
                setIsConnected(false);
                setConnectionError('Failed to connect to training server');
            } finally {
                if (cancelled) {
                    return;
                }
                const shouldContinue = isActive || backendActiveRef.current;
                if (shouldContinue && !trainingEnded) {
                    const elapsedMs = Date.now() - pollStartTime;
                    const delayMs = Math.max(0, pollIntervalRef.current - elapsedMs);
                    pollTimeoutRef.current = setTimeout(pollStatus, delayMs);
                }
            }
        };

        void pollStatus();

        return () => {
            cancelled = true;
            pollAbortRef.current?.abort();
            if (pollTimeoutRef.current) {
                clearTimeout(pollTimeoutRef.current);
                pollTimeoutRef.current = null;
            }
        };
    }, [isActive]);

    const chartPoints = useMemo(() => {
        if (historyPoints.length === 0) {
            return [];
        }
        const sortedPoints = historyPoints.slice().sort((a, b) => {
            if (a.epoch !== b.epoch) {
                return a.epoch - b.epoch;
            }
            return a.time_step - b.time_step;
        });
        const maxSteps = typeof stats.max_steps === 'number' && Number.isFinite(stats.max_steps)
            ? Math.max(1, stats.max_steps)
            : 1;
        return sortedPoints.map((point) => {
            const epochIndex = typeof point.epoch === 'number' ? Math.max(1, point.epoch) : 1;
            return {
                ...point,
                time_step: (epochIndex - 1) * maxSteps + point.time_step,
            };
        }).sort((a, b) => a.time_step - b.time_step);
    }, [historyPoints, stats.max_steps]);

    const progressRaw = stats.total_epochs > 0
        ? (stats.epoch / stats.total_epochs) * 100
        : 0;
    const progress = Number.isFinite(progressRaw)
        ? Math.min(100, Math.max(0, Math.round(progressRaw)))
        : 0;
    const progressRadius = 52;
    const progressCircumference = 2 * Math.PI * progressRadius;
    const progressOffset = progressCircumference * (1 - progress / 100);
    const progressGradientId = useId();

    const statusLabel = (() => {
        if (!isConnected) {
            return 'Disconnected';
        }
        if (stats.status === 'error') {
            return 'Error';
        }
        if (stats.status === 'exploration') {
            return 'Exploration';
        }
        if (stats.status === 'training') {
            if (stopRequested || isStopping) {
                return 'Stopping';
            }
            return 'Training';
        }
        if (stats.status === 'completed') {
            return 'Completed';
        }
        if (stats.status === 'cancelled' || stopRequested) {
            return 'Stopped';
        }
        return 'Connected';
    })();

    const statusClass = (() => {
        if (!isConnected) {
            return 'disconnected';
        }
        if (stats.status === 'error') {
            return 'error';
        }
        if (stats.status === 'exploration') {
            return 'exploration';
        }
        if (stats.status === 'training') {
            return 'training';
        }
        if (stats.status === 'completed') {
            return 'completed';
        }
        if (stats.status === 'cancelled' || stopRequested) {
            return 'stopped';
        }
        return 'connected';
    })();

    const handleStopTraining = async () => {
        if (isStopping) {
            return;
        }
        setIsStopping(true);
        setStopError(null);
        try {
            const response = await fetch('/api/training/stop', { method: 'POST' });
            if (!response.ok) {
                const errorPayload = await response.json();
                throw new Error(errorPayload.detail || 'Failed to stop training');
            }
            setStopRequested(true);
        } catch (err) {
            setStopError(err instanceof Error ? err.message : 'Failed to stop training');
        } finally {
            setIsStopping(false);
        }
    };

    const formatMetric = (value: number | null | undefined) => {
        if (value === null || value === undefined || !Number.isFinite(value)) {
            return 'N/A';
        }
        if (value === 0) {
            return '0';
        }
        const absoluteValue = Math.abs(value);
        if (absoluteValue < 0.0001) {
            return value.toExponential(3);
        }
        const maximumFractionDigits = absoluteValue < 0.01
            ? 6
            : absoluteValue < 1
                ? 4
                : 3;
        return value.toLocaleString(undefined, { maximumFractionDigits });
    };

    return (
        <div className="training-dashboard">
            <div className="training-dashboard-divider" />
            <div className="dashboard-header">
                <h3 className="dashboard-title">
                    <Activity size={20} />
                    Training Monitor
                </h3>
                <div className={`connection-status ${statusClass}`}>
                    <span className="connection-dot"></span>
                    {statusLabel}
                </div>
            </div>

            {connectionError && (
                <div className="dashboard-error">
                    <AlertCircle size={16} />
                    {connectionError}
                </div>
            )}

            {stopError && (
                <div className="dashboard-error">
                    <AlertCircle size={16} />
                    {stopError}
                </div>
            )}

            <div className="progress-section">
                <div className="metrics-progress-row">
                    <div className="metrics-panel">
                        <div className="metrics-grid">
                            <div className="metric-card loss">
                                <div className="metric-icon">
                                    <TrendingUp size={20} />
                                </div>
                                <div className="metric-content">
                                    <span className="metric-label">Loss</span>
                                    <span className="metric-value">{formatMetric(stats.loss)}</span>
                                </div>
                            </div>

                            <div className="metric-card rmse">
                                <div className="metric-icon">
                                    <Target size={20} />
                                </div>
                                <div className="metric-content">
                                    <span className="metric-label">RMSE</span>
                                    <span className="metric-value">{formatMetric(stats.rmse)}</span>
                                </div>
                            </div>

                            <div className="metric-card loss">
                                <div className="metric-icon">
                                    <TrendingUp size={20} />
                                </div>
                                <div className="metric-content">
                                    <span className="metric-label">Val Loss</span>
                                    <span className="metric-value">{formatMetric(stats.val_loss)}</span>
                                </div>
                            </div>

                            <div className="metric-card rmse">
                                <div className="metric-icon">
                                    <Target size={20} />
                                </div>
                                <div className="metric-content">
                                    <span className="metric-label">Val RMSE</span>
                                    <span className="metric-value">{formatMetric(stats.val_rmse)}</span>
                                </div>
                            </div>

                            <div className="metric-card total-reward">
                                <div className="metric-icon">
                                    <TrendingUp size={20} />
                                </div>
                                <div className="metric-content">
                                    <span className="metric-label">Total Reward</span>
                                    <span className="metric-value">{formatMetric(stats.total_reward)}</span>
                                </div>
                            </div>

                            <div className="metric-card capital-gain">
                                <div className="metric-icon">
                                    <ArrowUpRight size={20} />
                                </div>
                                <div className="metric-content">
                                    <span className="metric-label">Capital Gain</span>
                                    <span className="metric-value">{formatMetric(stats.capital_gain)}</span>
                                </div>
                            </div>

                            <div className="metric-card capital">
                                <div className="metric-icon">
                                    <DollarSign size={20} />
                                </div>
                                <div className="metric-content">
                                    <span className="metric-label">Capital</span>
                                    <span className="metric-value">{formatMetric(stats.capital)}</span>
                                </div>
                            </div>

                            <div className="metric-card capital">
                                <div className="metric-icon">
                                    <DollarSign size={20} />
                                </div>
                                <div className="metric-content">
                                    <span className="metric-label">Current Bet</span>
                                    <span className="metric-value">{formatMetric(stats.current_bet_amount ?? 0)}</span>
                                </div>
                            </div>
                        </div>

                        <div className="metrics-meta-row">
                            <div className="metric-card rmse metric-meta-card">
                                <div className="metric-icon">
                                    <Target size={20} />
                                </div>
                                <div className="metric-content">
                                    <span className="metric-label">Strategy</span>
                                    <span className="metric-value">{stats.current_strategy_name ?? 'Keep'}</span>
                                </div>
                            </div>

                            <div className="metric-card timestep metric-meta-card">
                                <div className="metric-icon">
                                    <Clock size={20} />
                                </div>
                                <div className="metric-content">
                                    <span className="metric-label">Time Step</span>
                                    <span className="metric-value">{formatMetric(stats.time_step)}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="progress-side">
                        <div className="progress-episode-label">
                            Episode {stats.epoch} / {stats.total_epochs}
                        </div>
                        <div
                            className="progress-wheel"
                            role="img"
                            aria-label={`Training progress: ${progress}%`}
                        >
                            <svg className="progress-wheel-svg" viewBox="0 0 120 120" aria-hidden="true">
                                <defs>
                                    <linearGradient id={progressGradientId} x1="0%" y1="0%" x2="100%" y2="100%">
                                        <stop offset="0%" stopColor="var(--roulette-green)" />
                                        <stop offset="100%" stopColor="#4ade80" />
                                    </linearGradient>
                                </defs>
                                <circle className="progress-wheel-track" cx="60" cy="60" r={progressRadius} />
                                <circle
                                    className="progress-wheel-fill"
                                    cx="60"
                                    cy="60"
                                    r={progressRadius}
                                    style={{
                                        strokeDasharray: progressCircumference,
                                        strokeDashoffset: progressOffset,
                                        stroke: `url(#${progressGradientId})`,
                                    }}
                                />
                            </svg>
                            <span className="progress-wheel-text">{progress}%</span>
                        </div>
                        <button
                            type="button"
                            className="stop-training-btn"
                            onClick={handleStopTraining}
                            disabled={isStopping || stats.status !== 'training'}
                        >
                            Stop
                        </button>
                    </div>
                </div>
            </div>

            <div className="dashboard-visuals">
                <div className="visual-card">
                    <div className="visual-card-header">
                        <span className="visual-card-title">Loss</span>
                        <div className="visual-card-legend">
                            <span className="legend-item"><span className="legend-dot loss"></span>Train</span>
                            <span className="legend-item legend-item-muted"><span className="legend-dot loss legend-dot-muted"></span>Validation</span>
                        </div>
                    </div>
                    <TrainingLossChart points={chartPoints} />
                </div>
                <div className="visual-card">
                    <div className="visual-card-header">
                        <span className="visual-card-title">Total Reward</span>
                        <div className="visual-card-legend">
                            <span className="legend-item"><span className="legend-dot total-reward"></span>Total Reward</span>
                        </div>
                    </div>
                    <TrainingMetricsChart points={chartPoints} />
                </div>
            </div>
        </div>
    );
};
