import React, { useState, useEffect, useRef } from 'react';
import { Activity, Zap, TrendingUp, DollarSign, Target, Clock, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';

import { TrainingLossChart, type TrainingHistoryPoint } from './TrainingLossChart';
import { TrainingRmseChart } from './TrainingRmseChart';

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
    onTrainingEnd?: () => void;
}

export const TrainingDashboard: React.FC<TrainingDashboardProps> = ({ isActive, onTrainingEnd }) => {
    const [stats, setStats] = useState<TrainingStats>({
        epoch: 0,
        total_epochs: 0,
        time_step: 0,
        loss: 0,
        rmse: 0,
        reward: 0,
        total_reward: 0,
        capital: 0,
        status: 'idle',
    });
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState<string | null>(null);
    const [historyPoints, setHistoryPoints] = useState<TrainingHistoryPoint[]>([]);
    const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const pollIntervalRef = useRef(1000);
    const isActiveRef = useRef(isActive);

    const maxHistoryPoints = 2000;

    useEffect(() => {
        isActiveRef.current = isActive;
    }, [isActive]);

    useEffect(() => {
        if (!isActive) {
            if (pollTimeoutRef.current) {
                clearTimeout(pollTimeoutRef.current);
                pollTimeoutRef.current = null;
            }
            setIsConnected(false);
            setConnectionError(null);
            return;
        }

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
                if (isActiveRef.current) {
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
    }, [isActive, onTrainingEnd]);

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

    return (
        <div className="training-dashboard">
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

            <div className="dashboard-status">
                {getStatusIcon()}
                <span>{getStatusText()}</span>
            </div>

            {stats.total_epochs > 0 && (
                <div className="progress-section">
                    <div className="progress-header">
                        <span>Epoch {stats.epoch} / {stats.total_epochs}</span>
                        <span>{progress}%</span>
                    </div>
                    <div className="progress-bar">
                        <div
                            className="progress-fill"
                            style={{ width: `${progress}%` }}
                        ></div>
                    </div>
                </div>
            )}

            <div className="metrics-grid">
                <div className="metric-card loss">
                    <div className="metric-icon">
                        <TrendingUp size={20} />
                    </div>
                    <div className="metric-content">
                        <span className="metric-label">Loss</span>
                        <span className="metric-value">{stats.loss.toFixed(6)}</span>
                    </div>
                </div>

                <div className="metric-card rmse">
                    <div className="metric-icon">
                        <Target size={20} />
                    </div>
                    <div className="metric-content">
                        <span className="metric-label">RMSE</span>
                        <span className="metric-value">{stats.rmse.toFixed(6)}</span>
                    </div>
                </div>

                <div className="metric-card reward">
                    <div className="metric-icon">
                        <Zap size={20} />
                    </div>
                    <div className="metric-content">
                        <span className="metric-label">Reward</span>
                        <span className="metric-value">{stats.reward}</span>
                    </div>
                </div>

                <div className="metric-card total-reward">
                    <div className="metric-icon">
                        <TrendingUp size={20} />
                    </div>
                    <div className="metric-content">
                        <span className="metric-label">Total Reward</span>
                        <span className="metric-value">{stats.total_reward}</span>
                    </div>
                </div>

                <div className="metric-card capital">
                    <div className="metric-icon">
                        <DollarSign size={20} />
                    </div>
                    <div className="metric-content">
                        <span className="metric-label">Capital</span>
                        <span className="metric-value">{stats.capital}</span>
                    </div>
                </div>

                <div className="metric-card timestep">
                    <div className="metric-icon">
                        <Clock size={20} />
                    </div>
                    <div className="metric-content">
                        <span className="metric-label">Time Step</span>
                        <span className="metric-value">{stats.time_step}</span>
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
                    <TrainingLossChart points={historyPoints} />
                </div>
                <div className="visual-card">
                    <div className="visual-card-header">
                        <span className="visual-card-title">RMSE</span>
                        <div className="visual-card-legend">
                            <span className="legend-item"><span className="legend-dot rmse"></span>Train</span>
                            <span className="legend-item" style={{ opacity: 0.7 }}><span className="legend-dot rmse" style={{ opacity: 0.5 }}></span>Validation</span>
                        </div>
                    </div>
                    <TrainingRmseChart points={historyPoints} />
                </div>
            </div>
        </div>
    );
};
