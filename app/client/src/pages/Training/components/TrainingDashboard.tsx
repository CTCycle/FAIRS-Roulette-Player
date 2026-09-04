import React, { useId, useMemo } from 'react';
import { Activity, AlertCircle, ArrowUpRight, Clock, DollarSign, Target, TrendingUp } from 'lucide-react';

import type {
    TrainingHistoryPoint,
    TrainingStatusSnapshot,
} from '../../../types/training';
import { TrainingLossChart } from './TrainingLossChart';
import { TrainingMetricsChart } from './TrainingMetricsChart';
import { TrainingMetricCard } from './TrainingMetricCard';
import './TrainingDashboardEnhancements.css';

interface TrainingDashboardProps {
    status: TrainingStatusSnapshot;
    isConnected: boolean;
    connectionError: string | null;
    isStopping: boolean;
    stopError: string | null;
    onStopTraining: () => Promise<void>;
}

const formatMetric = (value: number | null | undefined): string => {
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

export const TrainingDashboard: React.FC<TrainingDashboardProps> = ({
    status,
    isConnected,
    connectionError,
    isStopping,
    stopError,
    onStopTraining,
}) => {
    const stats = status.latest_stats;
    const historyPoints = status.history;
    const chartPoints = useMemo<TrainingHistoryPoint[]>(() => {
        if (historyPoints.length === 0) {
            return [];
        }
        const sortedPoints = historyPoints.slice().sort((a, b) => {
            if (a.epoch !== b.epoch) {
                return a.epoch - b.epoch;
            }
            return a.time_step - b.time_step;
        });
        const maxSteps = Math.max(1, stats.max_steps);
        return sortedPoints.map((point) => ({
            ...point,
            time_step: (Math.max(1, point.epoch) - 1) * maxSteps + point.time_step,
        })).sort((a, b) => a.time_step - b.time_step);
    }, [historyPoints, stats.max_steps]);

    const completedEpisodes = Math.max(0, stats.epoch - 1);
    const episodeFraction = stats.max_steps > 0
        ? Math.min(1, Math.max(0, (stats.time_step + 1) / stats.max_steps))
        : 0;
    const progressRaw = stats.status === 'completed'
        ? 100
        : stats.total_epochs > 0
            ? ((completedEpisodes + episodeFraction) / stats.total_epochs) * 100
            : 0;
    const progress = Number.isFinite(progressRaw)
        ? Math.min(100, Math.max(0, Math.round(progressRaw)))
        : 0;
    const progressRadius = 52;
    const progressCircumference = 2 * Math.PI * progressRadius;
    const progressOffset = progressCircumference * (1 - progress / 100);
    const progressGradientId = useId();

    const statusLabel = !isConnected
        ? 'Disconnected'
        : stats.status === 'error'
            ? 'Error'
            : stats.status === 'exploration'
                ? 'Replay warm-up'
                : stats.status === 'training'
                    ? (isStopping ? 'Stopping' : 'Training')
                    : stats.status === 'stopping'
                        ? 'Stopping'
                        : stats.status === 'completed'
                            ? 'Completed'
                            : stats.status === 'cancelled'
                                ? 'Stopped'
                                : 'Connected';

    const statusClass = !isConnected
        ? 'disconnected'
        : stats.status === 'error'
            ? 'error'
            : stats.status === 'exploration'
                ? 'exploration'
                : stats.status === 'training'
                    ? 'training'
                    : stats.status === 'completed'
                        ? 'completed'
                        : stats.status === 'cancelled' || stats.status === 'stopping'
                            ? 'stopped'
                            : 'connected';

    const replayProgress = stats.replay_buffer_size > 0
        ? `${Math.min(stats.experience_count, stats.replay_buffer_size).toLocaleString()} / ${stats.replay_buffer_size.toLocaleString()}`
        : 'N/A';
    const showRunMessage = Boolean(
        stats.message
        && ['completed', 'cancelled', 'error', 'stopping'].includes(stats.status),
    );

    return (
        <div className="training-dashboard">
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

            {showRunMessage && (
                <div className={`dashboard-status-message dashboard-status-${stats.status}`} role="status">
                    {stats.status === 'error' && <AlertCircle size={16} />}
                    <span>{stats.message}</span>
                </div>
            )}

            <div className="progress-section">
                <div className="metrics-progress-row">
                    <div className="metrics-panel">
                        <div className="metrics-groups" aria-label="Training metrics">
                            <section className="metric-group">
                                <h4 className="metric-group-title">Model quality</h4>
                                <div className="metric-group-grid">
                                    <TrainingMetricCard tone="loss" label="Loss" value={formatMetric(stats.loss)} Icon={TrendingUp} />
                                    <TrainingMetricCard tone="rmse" label="RMSE" value={formatMetric(stats.rmse)} Icon={Target} />
                                    <TrainingMetricCard tone="loss" label="Val Loss" value={formatMetric(stats.val_loss)} Icon={TrendingUp} />
                                    <TrainingMetricCard tone="rmse" label="Val RMSE" value={formatMetric(stats.val_rmse)} Icon={Target} />
                                </div>
                            </section>

                            <section className="metric-group">
                                <h4 className="metric-group-title">Training outcome</h4>
                                <div className="metric-group-grid">
                                    <TrainingMetricCard tone="total-reward" label="Total Reward" value={formatMetric(stats.total_reward)} Icon={TrendingUp} />
                                    <TrainingMetricCard tone="total-reward" label="Val Reward" value={formatMetric(stats.val_reward)} Icon={Target} />
                                    <TrainingMetricCard tone="capital-gain" label="Capital Gain" value={formatMetric(stats.capital_gain)} Icon={ArrowUpRight} />
                                    <TrainingMetricCard tone="capital" label="Capital" value={formatMetric(stats.capital)} Icon={DollarSign} />
                                </div>
                            </section>

                            <section className="metric-group metric-group-runtime">
                                <h4 className="metric-group-title">Run state</h4>
                                <div className="metric-group-grid metric-group-grid-runtime">
                                    <TrainingMetricCard tone="capital" label="Current Bet" value={formatMetric(stats.current_bet_amount)} Icon={DollarSign} />
                                    <TrainingMetricCard tone="rmse" label="Epsilon" value={formatMetric(stats.epsilon)} Icon={Target} />
                                    <TrainingMetricCard tone="rmse" label="Strategy" value={stats.current_strategy_name ?? 'Keep'} Icon={Target} />
                                    <TrainingMetricCard tone="timestep" label="Time Step" value={formatMetric(stats.time_step)} Icon={Clock} />
                                    <TrainingMetricCard tone="timestep" label="Replay Warm-up" value={replayProgress} Icon={Activity} />
                                </div>
                            </section>
                        </div>
                    </div>

                    <div className="progress-side">
                        <div className="progress-episode-label">
                            Episode {stats.epoch} / {stats.total_epochs}
                            {stats.max_steps > 0 && ` · Step ${stats.time_step} / ${stats.max_steps}`}
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
                            onClick={() => void onStopTraining()}
                            disabled={isStopping || stats.status === 'stopping' || !status.is_training}
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
