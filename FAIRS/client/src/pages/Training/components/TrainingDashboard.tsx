import React, { useState, useEffect, useRef } from 'react';
import { Activity, Zap, TrendingUp, DollarSign, Target, Clock, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';

interface TrainingStats {
    epoch: number;
    total_epochs: number;
    time_step: number;
    loss: number;
    rmse: number;
    reward: number;
    total_reward: number;
    capital: number;
    status: 'idle' | 'training' | 'completed' | 'error';
    message?: string;
}

interface TrainingRuntimeSettings {
    render_environment: boolean;
    render_update_frequency: number;
}

interface WebSocketMessage {
    type: 'connection' | 'update' | 'pong' | 'ping' | 'settings' | 'env';
    data?: TrainingStats | { is_training: boolean; latest_stats: TrainingStats; runtime_settings?: TrainingRuntimeSettings } | TrainingRuntimeSettings;
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
    const [runtimeSettings, setRuntimeSettings] = useState<TrainingRuntimeSettings>({
        render_environment: false,
        render_update_frequency: 50,
    });
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const settingsUpdateTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const patchRuntimeSettings = async (nextSettings: TrainingRuntimeSettings) => {
        try {
            const response = await fetch('/api/training/settings', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(nextSettings),
            });

            if (!response.ok) {
                const error = await response.json();
                console.error('Failed to update runtime settings:', error);
                return;
            }

            setRuntimeSettings(nextSettings);
        } catch (err) {
            console.error('Failed to update runtime settings:', err);
        }
    };

    useEffect(() => {
        const loadSettings = async () => {
            try {
                const response = await fetch('/api/training/settings');
                if (!response.ok) {
                    return;
                }
                const data = await response.json();
                if (data && typeof data === 'object') {
                    setRuntimeSettings(data as TrainingRuntimeSettings);
                }
            } catch (err) {
                console.error('Failed to load runtime settings:', err);
            }
        };

        loadSettings();
    }, []);

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

        const connectWebSocket = () => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
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
                        const connData = message.data as { is_training: boolean; latest_stats: TrainingStats; runtime_settings?: TrainingRuntimeSettings };
                        if (connData.latest_stats && Object.keys(connData.latest_stats).length > 0) {
                            setStats(connData.latest_stats);
                        }
                        if (connData.runtime_settings) {
                            setRuntimeSettings(connData.runtime_settings);
                        }
                    } else if (message.type === 'update' && message.data) {
                        const updatedStats = message.data as TrainingStats;
                        setStats(updatedStats);
                        // Notify parent when training ends
                        if (updatedStats.status === 'completed' || updatedStats.status === 'error') {
                            onTrainingEnd?.();
                        }
                    } else if (message.type === 'settings' && message.data) {
                        setRuntimeSettings(message.data as TrainingRuntimeSettings);
                    } else if (message.type === 'ping') {
                        ws.send('ping');
                    }
                } catch (err) {
                    console.error('Failed to parse WebSocket message:', err);
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
                // Only reconnect if still active
                if (isActive) {
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
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (settingsUpdateTimeoutRef.current) {
                clearTimeout(settingsUpdateTimeoutRef.current);
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

            <div className="dashboard-settings">
                <div className="dashboard-settings-row">
                    <input
                        type="checkbox"
                        id="renderEnvironment"
                        checked={runtimeSettings.render_environment}
                        onChange={(e) => {
                            const next = { ...runtimeSettings, render_environment: e.target.checked };
                            setRuntimeSettings(next);
                            patchRuntimeSettings(next);
                        }}
                    />
                    <label htmlFor="renderEnvironment" className="form-label" style={{ marginBottom: 0 }}>
                        Render environment every N steps
                    </label>
                    <input
                        type="number"
                        className="form-input"
                        min="1"
                        value={runtimeSettings.render_update_frequency}
                        disabled={!runtimeSettings.render_environment}
                        onChange={(e) => {
                            const value = Number(e.target.value);
                            const next = { ...runtimeSettings, render_update_frequency: value };
                            setRuntimeSettings(next);

                            if (settingsUpdateTimeoutRef.current) {
                                clearTimeout(settingsUpdateTimeoutRef.current);
                            }
                            settingsUpdateTimeoutRef.current = setTimeout(() => {
                                patchRuntimeSettings(next);
                            }, 300);
                        }}
                        style={{ width: '90px', marginLeft: 'auto' }}
                    />
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
        </div>
    );
};
