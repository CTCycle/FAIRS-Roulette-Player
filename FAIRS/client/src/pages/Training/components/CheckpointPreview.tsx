import React, { useEffect, useState } from 'react';
import { Activity, Info, RefreshCw, Save, X } from 'lucide-react';
import { useAppState } from '../../../context/AppStateContext';

interface CheckpointMetadataResponse {
    checkpoint: string;
    summary: Record<string, unknown>;
}

interface CheckpointPreviewProps {
    refreshKey?: number;
}

export const CheckpointPreview: React.FC<CheckpointPreviewProps> = ({
    refreshKey = 0,
}) => {
    const { state, dispatch } = useAppState();
    const { resumeConfig, isTraining } = state.training;
    const [checkpoints, setCheckpoints] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [metadataOpen, setMetadataOpen] = useState(false);
    const [metadataLoading, setMetadataLoading] = useState(false);
    const [metadataError, setMetadataError] = useState<string | null>(null);
    const [metadataPayload, setMetadataPayload] = useState<CheckpointMetadataResponse | null>(null);

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

    const loadCheckpointMetadata = async (checkpointName: string) => {
        const response = await fetch(`/api/training/checkpoints/${encodeURIComponent(checkpointName)}/metadata`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to load checkpoint metadata');
        }
        const payload = (await response.json()) as CheckpointMetadataResponse;
        return payload;
    };

    const openMetadataModal = async (checkpointName: string) => {
        setMetadataOpen(true);
        setMetadataLoading(true);
        setMetadataError(null);
        try {
            const payload = await loadCheckpointMetadata(checkpointName);
            setMetadataPayload(payload);
        } catch (err) {
            setMetadataPayload(null);
            setMetadataError(err instanceof Error ? err.message : 'Unable to load metadata');
        } finally {
            setMetadataLoading(false);
        }
    };

    const closeMetadataModal = () => {
        setMetadataOpen(false);
        setMetadataPayload(null);
        setMetadataError(null);
    };

    const handleResumeTraining = async (checkpointName: string) => {
        if (isTraining) {
            alert('Training is already in progress.');
            return;
        }

        try {
            const response = await fetch('/api/training/resume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    checkpoint: checkpointName,
                    additional_episodes: Number(resumeConfig.numAdditionalEpisodes),
                }),
            });

            if (!response.ok) {
                const errorPayload = await response.json();
                alert(`Failed to resume training: ${errorPayload.detail || 'Unknown error'}`);
                return;
            }

            dispatch({ type: 'SET_TRAINING_IS_TRAINING', payload: true });
        } catch (err) {
            alert('Failed to connect to training server');
        }
    };

    const handleEvaluateCheckpoint = async (checkpointName: string) => {
        try {
            const payload = await loadCheckpointMetadata(checkpointName);
            const summary = payload.summary || {};
            const datasetName = typeof summary.dataset_name === 'string' ? summary.dataset_name : '';
            const betAmount = typeof summary.bet_amount === 'number' ? summary.bet_amount : 1;
            const initialCapital = typeof summary.initial_capital === 'number' ? summary.initial_capital : 100;

            if (!datasetName) {
                alert('Checkpoint metadata does not include a dataset name. Select a checkpoint with a dataset to evaluate.');
                return;
            }

            const response = await fetch('/api/inference/sessions/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    checkpoint: checkpointName,
                    dataset_name: datasetName,
                    game_capital: Number(initialCapital),
                    game_bet: Number(betAmount),
                }),
            });

            if (!response.ok) {
                const errorPayload = await response.json();
                alert(`Failed to start evaluation: ${errorPayload.detail || 'Unknown error'}`);
                return;
            }

            const result = await response.json();
            alert(`Evaluation session started (session ${result.session_id}). Continue from the Inference page.`);
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Unable to start evaluation.');
        }
    };

    const buildMetadataRows = (summary: Record<string, unknown>) => {
        const rows = [
            { label: 'Dataset', key: 'dataset_name' },
            { label: 'Sample Size', key: 'sample_size' },
            { label: 'Seed', key: 'seed' },
            { label: 'Episodes', key: 'episodes' },
            { label: 'Batch Size', key: 'batch_size' },
            { label: 'Learning Rate', key: 'learning_rate' },
            { label: 'Perceptive Field', key: 'perceptive_field_size' },
            { label: 'QNet Neurons', key: 'neurons' },
            { label: 'Embedding Dims', key: 'embedding_dimensions' },
            { label: 'Exploration Rate', key: 'exploration_rate' },
            { label: 'Exploration Decay', key: 'exploration_rate_decay' },
            { label: 'Discount Rate', key: 'discount_rate' },
            { label: 'Update Frequency', key: 'model_update_frequency' },
            { label: 'Final Loss', key: 'final_loss' },
            { label: 'Final RMSE', key: 'final_rmse' },
            { label: 'Val Loss', key: 'final_val_loss' },
            { label: 'Val RMSE', key: 'final_val_rmse' },
        ];

        return rows
            .map((row) => {
                if (row.key === 'dataset_name') {
                    const datasetValue = summary[row.key];
                    const datasetName = typeof datasetValue === 'string' ? datasetValue : '';
                    return {
                        label: row.label,
                        value: datasetName || 'All datasets',
                    };
                }
                return {
                    label: row.label,
                    value: summary[row.key],
                };
            })
            .filter((row) => row.value !== null && row.value !== undefined && row.value !== '');
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
                                <span className="preview-row-spacer" />
                                <div className="preview-row-actions">
                                    <button
                                        className="preview-row-icon preview-row-icon-metadata"
                                        onClick={() => openMetadataModal(name)}
                                        title="View checkpoint metadata"
                                    >
                                        <Info size={16} />
                                    </button>
                                    <button
                                        className="preview-row-icon preview-row-icon-evaluate"
                                        onClick={() => handleEvaluateCheckpoint(name)}
                                        title="Evaluate checkpoint"
                                    >
                                        <Activity size={16} />
                                    </button>
                                    <button
                                        className="preview-row-icon preview-row-icon-resume"
                                        onClick={() => handleResumeTraining(name)}
                                        title="Resume training from this checkpoint"
                                        disabled={isTraining}
                                    >
                                        <RefreshCw size={16} />
                                    </button>
                                    <button
                                        className="preview-row-delete"
                                        onClick={() => handleDelete(name)}
                                        title="Delete Checkpoint"
                                    >
                                        <X size={16} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            {metadataOpen && (
                <div className="preview-modal-overlay" onClick={closeMetadataModal}>
                    <div className="preview-modal" onClick={(event) => event.stopPropagation()}>
                        <div className="preview-modal-header">
                            <div className="preview-modal-title">
                                <Info size={18} />
                                Checkpoint Metadata
                            </div>
                            <button className="preview-modal-close" onClick={closeMetadataModal} title="Close">
                                <X size={16} />
                            </button>
                        </div>
                        {metadataLoading && (
                            <div className="preview-loading">Loading metadata...</div>
                        )}
                        {!metadataLoading && metadataError && (
                            <div className="preview-error">{metadataError}</div>
                        )}
                        {!metadataLoading && !metadataError && metadataPayload && (
                            <div className="preview-modal-list">
                                {buildMetadataRows(metadataPayload.summary).map((row) => (
                                    <div key={row.label} className="preview-modal-row">
                                        <span className="preview-modal-label">{row.label}</span>
                                        <span className="preview-modal-value">
                                            {typeof row.value === 'number'
                                                ? row.value.toLocaleString()
                                                : String(row.value)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};
