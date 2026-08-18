import React from 'react';
import { Lightbulb, X } from 'lucide-react';
import { useGuidance } from './GuidanceContext';

interface FeatureTipProps {
    id: string;
    version?: number;
    title: string;
    children: React.ReactNode;
    action?: React.ReactNode;
    className?: string;
}

export const FeatureTip: React.FC<FeatureTipProps> = ({
    id,
    version = 1,
    title,
    children,
    action,
    className = '',
}) => {
    const { getStatus, markDismissed } = useGuidance();
    const status = getStatus(id, version);

    if (status) {
        return null;
    }

    return (
        <aside className={`guidance-feature-tip ${className}`.trim()} aria-label={title}>
            <Lightbulb size={17} aria-hidden="true" />
            <div className="guidance-feature-tip-copy">
                <strong>{title}</strong>
                <div>{children}</div>
                {action && <div className="guidance-feature-tip-action">{action}</div>}
            </div>
            <button
                type="button"
                className="guidance-tip-dismiss"
                onClick={() => markDismissed(id, version)}
                aria-label={`Dismiss ${title}`}
            >
                <X size={15} aria-hidden="true" />
            </button>
        </aside>
    );
};
