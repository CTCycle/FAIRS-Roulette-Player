import React, { useEffect, useMemo, useState } from 'react';
import { Activity, Check, ChevronLeft, ChevronRight, Info, RefreshCw, Save, X } from 'lucide-react';
import { useAppState } from '../../../context/AppStateContext';

interface CheckpointMetadataResponse {
    checkpoint: string;
    summary: Record<string, unknown>;
}

interface CheckpointPreviewProps {
    refreshKey?: number;
}

interface DatasetInfo {
    datasetId: string;
    datasetName: string;
}

type ResumeWizardStep = 0 | 1;

const RESUME_STEPS = ['Resume Configuration', 'Summary'] as const;

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
    const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
    const [datasetsLoading, setDatasetsLoading] = useState(false);
    const [datasetsError, setDatasetsError] = useState<string | null>(null);
    const [metadataCache, setMetadataCache] = useState<Record<string, CheckpointMetadataResponse>>({});
    const [checkpointDatasetMap, setCheckpointDatasetMap] = useState<Record<string, string>>({});

    const [resumeWizardOpen, setResumeWizardOpen] = useState(false);
    const [resumeWizardStep, setResumeWizardStep] = useState<ResumeWizardStep>(0);
    const [resumeWizardCheckpoint, setResumeWizardCheckpoint] = useState<string | null>(null);
    const [resumeWizardError, setResumeWizardError] = useState<string | null>(null);
    const [resumeSubmitting, setResumeSubmitting] = useState(false);

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

    const loadDatasets = async () => {
        setDatasetsLoading(true);
        setDatasetsError(null);
        try {
            const response = await fetch('/api/database/roulette-series/datasets');
            if (!response.ok) {
                throw new Error('Failed to load datasets');
            }
            const payload = await response.json();
            const datasetList = Array.isArray(payload?.datasets)
                ? payload.datasets
                    .filter((entry: unknown) => typeof entry === 'object' && entry !== null)
                    .map((entry: { dataset_id?: unknown; dataset_name?: unknown }) => ({
                        datasetId: typeof entry.dataset_id === 'string' ? entry.dataset_id : '',
                        datasetName: typeof entry.dataset_name === 'string' ? entry.dataset_name : '',
                    }))
                    .filter((entry: DatasetInfo) =>
                        entry.datasetId.trim().length > 0 && entry.datasetName.trim().length > 0
                    )
                : [];
            setDatasets(datasetList);
        } catch (err) {
            setDatasets([]);
            setDatasetsError('Unable to load dataset names.');
        } finally {
            setDatasetsLoading(false);
        }
    };

    useEffect(() => {
        void loadCheckpoints();
    }, [refreshKey]);

    useEffect(() => {
        void loadDatasets();
    }, [refreshKey]);

    const handleRefreshOverview = async () => {
        setMetadataCache({});
        setCheckpointDatasetMap({});
        await Promise.all([loadCheckpoints(), loadDatasets()]);
    };

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

    const cacheCheckpointMetadata = (checkpointName: string, payload: CheckpointMetadataResponse) => {
        setMetadataCache((prev) => ({ ...prev, [checkpointName]: payload }));
        const summary = payload.summary || {};
        const datasetId = typeof summary.dataset_id === 'string' ? summary.dataset_id : '';
        setCheckpointDatasetMap((prev) => ({ ...prev, [checkpointName]: datasetId }));
    };

    const prefetchCheckpointMetadata = async (checkpointList: string[]) => {
        const toFetch = checkpointList.filter((name) => !metadataCache[name]);
        if (toFetch.length === 0) {
            return;
        }
        const results = await Promise.all(
            toFetch.map(async (name) => {
                try {
                    const payload = await loadCheckpointMetadata(name);
                    return { name, payload };
                } catch (err) {
                    return { name, payload: null };
                }
            })
        );
        results.forEach((result) => {
            if (result.payload) {
                cacheCheckpointMetadata(result.name, result.payload);
            }
        });
    };

    useEffect(() => {
        if (checkpoints.length === 0) {
            return;
        }
        void prefetchCheckpointMetadata(checkpoints);
    }, [checkpoints, metadataCache]);

    const openMetadataModal = async (checkpointName: string) => {
        setMetadataOpen(true);
        setMetadataLoading(true);
        setMetadataError(null);
        try {
            const cached = metadataCache[checkpointName];
            if (cached) {
                setMetadataPayload(cached);
                return;
            }
            const payload = await loadCheckpointMetadata(checkpointName);
            cacheCheckpointMetadata(checkpointName, payload);
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

    const handleResumeTraining = async () => {
        if (isTraining) {
            alert('Training is already in progress.');
            return;
        }
        if (!resumeWizardCheckpoint) {
            setResumeWizardError('Select a checkpoint to resume.');
            return;
        }

        setResumeSubmitting(true);
        setResumeWizardError(null);

        try {
            const response = await fetch('/api/training/resume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    checkpoint: resumeWizardCheckpoint,
                    additional_episodes: Number(resumeConfig.numAdditionalEpisodes),
                }),
            });

            if (!response.ok) {
                const errorPayload = await response.json();
                setResumeWizardError(`Failed to resume training: ${errorPayload.detail || 'Unknown error'}`);
                return;
            }

            dispatch({ type: 'SET_TRAINING_IS_TRAINING', payload: true });
            closeResumeWizard();
        } catch (err) {
            setResumeWizardError('Failed to connect to training server');
        } finally {
            setResumeSubmitting(false);
        }
    };

    const handleEvaluateCheckpoint = async (checkpointName: string) => {
        try {
            const payload = metadataCache[checkpointName] ?? await loadCheckpointMetadata(checkpointName);
            if (!metadataCache[checkpointName]) {
                cacheCheckpointMetadata(checkpointName, payload);
            }
            const summary = payload.summary || {};
            const datasetId = typeof summary.dataset_id === 'string' ? summary.dataset_id : '';
            const betAmount = typeof summary.bet_amount === 'number' ? summary.bet_amount : 1;
            const initialCapital = typeof summary.initial_capital === 'number' ? summary.initial_capital : 100;

            if (!datasetId) {
                alert('Checkpoint metadata does not include a dataset identifier.');
                return;
            }

            const response = await fetch('/api/inference/sessions/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    checkpoint: checkpointName,
                    dataset_id: datasetId,
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
            { label: 'Dataset ID', key: 'dataset_id' },
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
            .map((row) => ({
                label: row.label,
                value: summary[row.key],
            }))
            .filter((row) => row.value !== null && row.value !== undefined && row.value !== '');
    };

    const openResumeWizard = async (checkpointName: string) => {
        if (isTraining) {
            alert('Training is already in progress.');
            return;
        }
        setResumeWizardOpen(true);
        setResumeWizardStep(0);
        setResumeWizardError(null);
        setResumeWizardCheckpoint(checkpointName);
        dispatch({ type: 'SET_TRAINING_RESUME_CONFIG', payload: { selectedCheckpoint: checkpointName } });

        if (!metadataCache[checkpointName]) {
            try {
                const payload = await loadCheckpointMetadata(checkpointName);
                cacheCheckpointMetadata(checkpointName, payload);
            } catch (err) {
                setResumeWizardError('Unable to load checkpoint metadata.');
            }
        }
    };

    const closeResumeWizard = () => {
        if (resumeSubmitting) {
            return;
        }
        setResumeWizardOpen(false);
        setResumeWizardStep(0);
        setResumeWizardCheckpoint(null);
        setResumeWizardError(null);
    };

    const handleResumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        dispatch({
            type: 'SET_TRAINING_RESUME_CONFIG',
            payload: { [name]: Number(value) },
        });
    };

    const availableDatasetSet = useMemo(
        () => new Set(datasets.map((entry) => entry.datasetId)),
        [datasets],
    );

    const resumeSummaryRows = useMemo(() => {
        if (!resumeWizardCheckpoint) {
            return [];
        }
        const summary = metadataCache[resumeWizardCheckpoint]?.summary || {};
        return [
            { label: 'Checkpoint', value: resumeWizardCheckpoint },
            ...buildMetadataRows(summary),
            { label: 'Additional Episodes', value: resumeConfig.numAdditionalEpisodes },
        ];
    }, [metadataCache, resumeConfig.numAdditionalEpisodes, resumeWizardCheckpoint]);

    return (
        <div className="checkpoint-preview">
            <div className="preview-header">
                <Save size={18} />
                <span>Available Checkpoints</span>
                <div className="preview-header-actions">
                    <button
                        className="preview-row-icon preview-header-refresh"
                        onClick={handleRefreshOverview}
                        title="Refresh checkpoints overview"
                        disabled={loading || datasetsLoading}
                    >
                        <RefreshCw size={16} />
                    </button>
                </div>
            </div>
            <div className="preview-content">
                {loading && <div className="preview-loading">Loading...</div>}
                {error && <div className="preview-error">{error}</div>}
                {!loading && !error && checkpoints.length === 0 && (
                    <div className="preview-empty">No checkpoints available</div>
                )}
                {!loading && !error && checkpoints.length > 0 && (
                    <div className="preview-list">
                        {checkpoints.map((name) => {
                            const datasetId = checkpointDatasetMap[name];
                            const canResume = datasetId && availableDatasetSet.has(datasetId);
                            return (
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
                                        {canResume && (
                                            <button
                                                className="preview-row-icon preview-row-icon-resume"
                                                onClick={() => openResumeWizard(name)}
                                                title="Resume training from this checkpoint"
                                                disabled={isTraining || datasetsLoading || Boolean(datasetsError)}
                                            >
                                                <RefreshCw size={16} />
                                            </button>
                                        )}
                                        <button
                                            className="preview-row-delete"
                                            onClick={() => handleDelete(name)}
                                            title="Delete Checkpoint"
                                        >
                                            <X size={16} />
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
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

            {resumeWizardOpen && (
                <div className="wizard-modal-overlay">
                    <div className="wizard-modal" role="dialog" aria-modal="true">
                        <div className="wizard-modal-header">
                            <div className="wizard-modal-title">
                                <RefreshCw size={18} />
                                Resume Training Wizard
                            </div>
                            <button className="wizard-modal-close" onClick={closeResumeWizard} title="Close">
                                <X size={16} />
                            </button>
                        </div>
                        <div className="wizard-modal-subtitle">
                            <span>Checkpoint: {resumeWizardCheckpoint}</span>
                            <span>{`Step ${resumeWizardStep + 1} of ${RESUME_STEPS.length}`}</span>
                        </div>
                        <div className="wizard-step-title">{RESUME_STEPS[resumeWizardStep]}</div>
                        <div className="wizard-step-content">
                            {resumeWizardStep === 0 && (
                                <div className="wizard-stack">
                                    <div className="form-group">
                                        <label className="form-label">Additional number of epochs</label>
                                        <input
                                            type="number"
                                            name="numAdditionalEpisodes"
                                            value={resumeConfig.numAdditionalEpisodes}
                                            onChange={handleResumeChange}
                                            className="form-input"
                                            min="1"
                                        />
                                    </div>
                                </div>
                            )}
                            {resumeWizardStep === 1 && (
                                <div className="wizard-summary">
                                    {resumeSummaryRows.map((row) => (
                                        <div key={row.label} className="wizard-summary-row">
                                            <span className="wizard-summary-label">{row.label}</span>
                                            <span className="wizard-summary-value">
                                                {typeof row.value === 'number'
                                                    ? row.value.toLocaleString()
                                                    : String(row.value)}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        {resumeWizardError && (
                            <div className="wizard-error">{resumeWizardError}</div>
                        )}
                        <div className="wizard-actions">
                            <button
                                type="button"
                                className="wizard-btn wizard-btn-secondary"
                                onClick={closeResumeWizard}
                                disabled={resumeSubmitting}
                            >
                                Cancel
                            </button>
                            <div className="wizard-actions-right">
                                <button
                                    type="button"
                                    className="wizard-btn wizard-btn-secondary"
                                    onClick={() => setResumeWizardStep((prev) => Math.max(0, prev - 1) as ResumeWizardStep)}
                                    disabled={resumeWizardStep === 0 || resumeSubmitting}
                                >
                                    <ChevronLeft size={16} />
                                    Previous
                                </button>
                                {resumeWizardStep < RESUME_STEPS.length - 1 ? (
                                    <button
                                        type="button"
                                        className="wizard-btn wizard-btn-primary"
                                        onClick={() => setResumeWizardStep((prev) => Math.min(RESUME_STEPS.length - 1, prev + 1) as ResumeWizardStep)}
                                        disabled={resumeSubmitting}
                                    >
                                        Next
                                        <ChevronRight size={16} />
                                    </button>
                                ) : (
                                    <button
                                        type="button"
                                        className="wizard-btn wizard-btn-primary"
                                        onClick={handleResumeTraining}
                                        disabled={resumeSubmitting}
                                    >
                                        <Check size={16} />
                                        Confirm
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
