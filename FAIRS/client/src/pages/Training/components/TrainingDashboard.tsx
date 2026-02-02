import React, { useMemo, useState, useEffect, useRef, useId } from 'react';
import { Activity, ArrowUpRight, TrendingUp, DollarSign, Target, Clock, AlertCircle } from 'lucide-react';

import { TrainingLossChart, type TrainingHistoryPoint } from './TrainingLossChart';
import { TrainingMetricsChart } from './TrainingMetricsChart';

interface TrainingStats {
    epoch: number;
    total_epochs: number;
    time_step: number;
    loss: number;
    rmse: number;
    val_loss?: number;
    val_rmse?: number;
    reward: number;
    val_reward?: number;
    total_reward: number;
    capital: number;
    capital_gain: number;
    status: 'idle' | 'training' | 'completed' | 'error' | 'cancelled';
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
    const [stats, setStats] = useState<TrainingStats>({
        epoch: 0,
        total_epochs: 0,
        time_step: 0,
        loss: 0,
        rmse: 0,
        reward: 0,
        total_reward: 0,
        capital: 0,
        capital_gain: 0,
        status: 'idle',
    });
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState<string | null>(null);
    const [historyPoints, setHistoryPoints] = useState<TrainingHistoryPoint[]>([]);
    const [isStopping, setIsStopping] = useState(false);
    const [stopRequested, setStopRequested] = useState(false);
    const [stopError, setStopError] = useState<string | null>(null);
    const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const pollIntervalRef = useRef(1000);
    const isActiveRef = useRef(isActive);
    const backendActiveRef = useRef(false);

    const maxHistoryPoints = 2000;

    useEffect(() => {
        isActiveRef.current = isActive;
    }, [isActive]);

    useEffect(() => {
        if (isActive) {
            setStopRequested(false);
            setStopError(null);
        }
    }, [isActive]);

    useEffect(() => {
        setHistoryPoints([]);
        setConnectionError(null);

        const pollStatus = async () => {
            try {
                const response = await fetch('/api/training/status');
                if (!response.ok) {
                    throw new Error(`Failed to fetch training status (${response.status})`);
                }
                const payload = (await response.json()) as TrainingStatusResponse;
                setIsConnected(true);
                setConnectionError(null);

                const backendActive = Boolean(payload.is_training);
                if (backendActive && !backendActiveRef.current) {
                    backendActiveRef.current = true;
                    onTrainingStart?.();
                } else if (!backendActive && backendActiveRef.current) {
                    backendActiveRef.current = false;
                    onTrainingEnd?.();
                }

                if (payload.latest_stats) {
                    setStats(payload.latest_stats);
                    if (payload.latest_stats.status === 'completed' || payload.latest_stats.status === 'error' || payload.latest_stats.status === 'cancelled') {
                        onTrainingEnd?.();
                    }
                }

                if (Array.isArray(payload.history)) {
                    setHistoryPoints(payload.history.slice(-maxHistoryPoints));
                }

                if (typeof payload.poll_interval === 'number' && payload.poll_interval > 0) {
                    pollIntervalRef.current = Math.max(250, payload.poll_interval * 1000);
                }
            } catch (err) {
                setIsConnected(false);
                setConnectionError('Failed to connect to training server');
            } finally {
                if (isActiveRef.current || backendActiveRef.current) {
                    pollTimeoutRef.current = setTimeout(pollStatus, pollIntervalRef.current);
                }
            }
        };

        void pollStatus();

        return () => {
            if (pollTimeoutRef.current) {
                clearTimeout(pollTimeoutRef.current);
                pollTimeoutRef.current = null;
            }
        };
    }, [onTrainingEnd, onTrainingStart]);

    const episodePoints = useMemo(() => {
        if (historyPoints.length === 0) {
            return [];
        }
        const byEpisode = new Map<number, TrainingHistoryPoint>();
        historyPoints.forEach((point) => {
            if (typeof point.epoch !== 'number' || point.epoch <= 0) {
                return;
            }
            byEpisode.set(point.epoch, { ...point, time_step: point.epoch });
        });
        return Array.from(byEpisode.values()).sort((a, b) => a.epoch - b.epoch);
    }, [historyPoints]);

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

    const formatMetric = (value: number) => {
        if (!Number.isFinite(value)) {
            return '0';
        }
        return value.toLocaleString(undefined, { maximumFractionDigits: 6 });
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

                        <div className="metric-card timestep">
                            <div className="metric-icon">
                                <Clock size={20} />
                            </div>
                            <div className="metric-content">
                                <span className="metric-label">Time Step</span>
                                <span className="metric-value">{formatMetric(stats.time_step)}</span>
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
                            <span className="legend-item" style={{ opacity: 0.7 }}><span className="legend-dot loss" style={{ opacity: 0.5 }}></span>Validation</span>
                        </div>
                    </div>
                    <TrainingLossChart points={episodePoints} />
                </div>
                <div className="visual-card">
                    <div className="visual-card-header">
                        <span className="visual-card-title">Metrics</span>
                        <div className="visual-card-legend">
                            <span className="legend-item"><span className="legend-dot total-reward"></span>Total Reward</span>
                            <span className="legend-item" style={{ opacity: 0.7 }}><span className="legend-dot capital"></span>Capital Gain</span>
                        </div>
                    </div>
                    <TrainingMetricsChart points={episodePoints} />
                </div>
            </div>
        </div>
    );
};
