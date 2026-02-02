import React, { useMemo, useState, useEffect, useRef } from 'react';
import { Activity, ArrowUpRight, TrendingUp, DollarSign, Target, Clock, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';

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

    const progress = stats.total_epochs > 0
        ? Math.round((stats.epoch / stats.total_epochs) * 100)
        : 0;

    const getStatusIcon = () => {
        switch (stats.status) {
            case 'training':
                return <Activity size={18} className="status-icon training" />;
            case 'completed':
                return <CheckCircle2 size={18} className="status-icon completed" />;
            case 'error':
            case 'cancelled':
                return <XCircle size={18} className="status-icon error" />;
            default:
                return <Clock size={18} className="status-icon idle" />;
        }
    };

    const getStatusText = () => {
        switch (stats.status) {
            case 'training':
                if (stopRequested || isStopping) {
                    return 'Stopping training...';
                }
                return 'Training in progress...';
            case 'completed':
                return 'Training completed';
            case 'cancelled':
                return 'Training cancelled';
            case 'error':
                return stats.message || 'Training error';
            default:
                return 'Waiting to start';
        }
    };

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
                <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                    <span className="connection-dot"></span>
                    {isConnected ? 'Connected' : 'Disconnected'}
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

            <div className="dashboard-status">
                {getStatusIcon()}
                <span>{getStatusText()}</span>
            </div>

            <div className="progress-section">
                <div className="progress-header">
                    <span>Episode {stats.epoch} / {stats.total_epochs}</span>
                    <span>{progress}%</span>
                </div>
                <div className="progress-row">
                    <div className="progress-bar">
                        <div
                            className="progress-fill"
                            style={{ width: `${progress}%` }}
                        ></div>
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
