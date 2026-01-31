import React, { useEffect, useState } from 'react';
import { Save, X } from 'lucide-react';

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

    const handleDelete = async (checkpointName: string) => {
        if (!confirm(`Are you sure you want to delete checkpoint "${checkpointName}"?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/training/checkpoints/${checkpointName}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to delete checkpoint');
            }

            // Remove the deleted checkpoint from the local state
            setCheckpoints((prev) => prev.filter((name) => name !== checkpointName));
        } catch (err) {
            console.error('Error deleting checkpoint:', err);
            alert(`Error deleting checkpoint: ${err instanceof Error ? err.message : String(err)}`);
        }
    };

    return (
        <div className="checkpoint-preview">
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
                                <button
                                    className="preview-delete-btn"
                                    onClick={() => handleDelete(name)}
                                    title="Delete Checkpoint"
                                    style={{
                                        background: 'none',
                                        border: 'none',
                                        cursor: 'pointer',
                                        color: '#ef4444',
                                        display: 'flex',
                                        alignItems: 'center',
                                        padding: '4px',
                                        marginLeft: 'auto',
                                    }}
                                >
                                    <X size={16} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
