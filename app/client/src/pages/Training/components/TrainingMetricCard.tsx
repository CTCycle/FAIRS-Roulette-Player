import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface TrainingMetricCardProps {
    tone: 'loss' | 'rmse' | 'total-reward' | 'capital-gain' | 'capital' | 'timestep';
    label: string;
    value: string;
    Icon: LucideIcon;
    compact?: boolean;
}

export const TrainingMetricCard: React.FC<TrainingMetricCardProps> = ({
    tone,
    label,
    value,
    Icon,
    compact = false,
}) => {
    const metricClassName = compact
        ? `metric-item ${tone} metric-meta-item`
        : `metric-item ${tone}`;

    return (
        <div className={metricClassName}>
            <div className="metric-icon">
                <Icon size={20} />
            </div>
            <div className="metric-content">
                <span className="metric-label">{label}</span>
                <span className="metric-value">{value}</span>
            </div>
        </div>
    );
};

