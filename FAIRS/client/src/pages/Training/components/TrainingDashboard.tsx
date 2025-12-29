import React, { useState, useEffect, useRef } from 'react';
import { Activity, Zap, TrendingUp, DollarSign, Target, Clock, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';

import { TrainingLossChart, type TrainingHistoryPoint } from './TrainingLossChart';

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
    status: 'idle' | 'training' | 'completed' | 'error';
    message?: string;
}

interface TrainingRuntimeSettings {
    render_environment: boolean;
    render_update_frequency: number;
}

interface TrainingEnvPayload {
    episode: number;
    time_step: number;
    action: number;
    extraction: number;
    reward: number;
    total_reward: number;
    capital: number;
    image_base64?: string;
    image_mime?: string;
}

interface TrainingConnectionPayload {
    is_training: boolean;
    latest_stats: TrainingStats;
    runtime_settings?: TrainingRuntimeSettings;
    history?: TrainingHistoryPoint[];
    latest_env?: TrainingEnvPayload;
}

interface WebSocketMessage {
    type: 'connection' | 'update' | 'pong' | 'ping' | 'settings' | 'env';
    data?: TrainingStats | TrainingConnectionPayload | TrainingRuntimeSettings | TrainingEnvPayload;
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
    const [_envPayload, setEnvPayload] = useState<TrainingEnvPayload | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const isActiveRef = useRef(isActive);

    const maxHistoryPoints = 2000;

    useEffect(() => {
        isActiveRef.current = isActive;
    }, [isActive]);


    useEffect(() => {
        // Only connect when training is active
        if (!isActive) {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }
            setIsConnected(false);
            setConnectionError(null);
            return;
        }

        setHistoryPoints([]);
        setEnvPayload(null);

        const connectWebSocket = () => {
            if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
                return;
            }

            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/api/training/ws`;
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                setIsConnected(true);
                setConnectionError(null);
            };

            ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);

                    if (message.type === 'connection' && message.data) {
                        const connData = message.data as TrainingConnectionPayload;
                        if (connData.latest_stats && Object.keys(connData.latest_stats).length > 0) {
                            setStats(connData.latest_stats);
                        }
                        if (connData.history && Array.isArray(connData.history)) {
                            setHistoryPoints(connData.history.slice(-maxHistoryPoints));
                        }
                        if (connData.latest_env && typeof connData.latest_env === 'object') {
                            setEnvPayload(connData.latest_env);
                        }
                    } else if (message.type === 'update' && message.data) {
                        const updatedStats = message.data as TrainingStats;
                        setStats(updatedStats);
                        if (updatedStats.status === 'training' && updatedStats.time_step > 0) {
                            const nextPoint: TrainingHistoryPoint = {
                                time_step: updatedStats.time_step,
                                loss: updatedStats.loss,
                                rmse: updatedStats.rmse,
                                val_loss: updatedStats.val_loss,
                                val_rmse: updatedStats.val_rmse,
                                epoch: updatedStats.epoch,
                            };
                            setHistoryPoints((prev) => {
                                if (prev.length && prev[prev.length - 1].time_step === nextPoint.time_step) {
                                    const next = prev.slice(0, -1).concat([nextPoint]);
                                    return next;
                                }
                                const next = prev.concat([nextPoint]);
                                return next.length > maxHistoryPoints ? next.slice(-maxHistoryPoints) : next;
                            });
                        }
                        // Notify parent when training ends
                        if (updatedStats.status === 'completed' || updatedStats.status === 'error') {
                            onTrainingEnd?.();
                        }
                    } else if (message.type === 'env' && message.data) {
                        setEnvPayload(message.data as TrainingEnvPayload);
                    } else if (message.type === 'ping') {
                        ws.send('ping');
                    }
                } catch (err) {
                    console.error('Failed to parse WebSocket message:', err);
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
                if (wsRef.current === ws) {
                    wsRef.current = null;
                }
                // Only reconnect if still active
                if (isActiveRef.current) {
                    reconnectTimeoutRef.current = setTimeout(() => {
                        connectWebSocket();
                    }, 3000);
                }
            };

            ws.onerror = () => {
                setConnectionError('Failed to connect to training server');
                setIsConnected(false);
            };

            wsRef.current = ws;
        };

        connectWebSocket();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [isActive]);

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
            case 'error':
                return stats.message || 'Training error';
            default:
                return 'Waiting to start';
        }
    };

    // Environment image source - logic preserved but not rendered in UI
    // const envImageSrc = envPayload?.image_base64
    //     ? `data:${envPayload.image_mime || 'image/png'};base64,${envPayload.image_base64}`
    //     : null;

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
                        <span className="visual-card-title">Real-time Loss</span>
                        <div className="visual-card-legend">
                            <span className="legend-item"><span className="legend-dot loss"></span>Loss (train)</span>
                            <span className="legend-item"><span className="legend-dot rmse"></span>RMSE (train)</span>
                            <span className="legend-item" style={{ opacity: 0.7 }}><span className="legend-dot loss" style={{ opacity: 0.5 }}></span>Loss (validation, dashed)</span>
                            <span className="legend-item" style={{ opacity: 0.7 }}><span className="legend-dot rmse" style={{ opacity: 0.5 }}></span>RMSE (validation, dashed)</span>
                        </div>
                    </div>
                    <TrainingLossChart points={historyPoints} />
                </div>
            </div>
        </div>
    );
};
