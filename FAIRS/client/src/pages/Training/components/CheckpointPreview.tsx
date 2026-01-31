import React, { useEffect, useState } from 'react';
import { Save } from 'lucide-react';

interface CheckpointPreviewProps {
    refreshKey?: number;
}

export const CheckpointPreview: React.FC<CheckpointPreviewProps> = ({
    refreshKey = 0,
}) => {
    const [checkpoints, setCheckpoints] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadCheckpoints = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/training/checkpoints');
            if (!response.ok) {
                throw new Error('Failed to load checkpoints');
            }
            const data = await response.json();
            const checkpointList = Array.isArray(data) ? data : [];
            setCheckpoints(checkpointList);
        } catch (err) {
            setError('Unable to load checkpoints.');
            setCheckpoints([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void loadCheckpoints();
    }, [refreshKey]);

    return (
        <div className="preview-panel checkpoint-preview">
            <div className="preview-header">
                <Save size={18} />
                <span>Available Checkpoints</span>
            </div>
            <div className="preview-content">
                {loading && <div className="preview-loading">Loading...</div>}
                {error && <div className="preview-error">{error}</div>}
                {!loading && !error && checkpoints.length === 0 && (
                    <div className="preview-empty">No checkpoints available</div>
                )}
                {!loading && !error && checkpoints.length > 0 && (
                    <div className="preview-list">
                        {checkpoints.map((name) => (
                            <div key={name} className="preview-row">
                                <span className="preview-row-name">{name}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
