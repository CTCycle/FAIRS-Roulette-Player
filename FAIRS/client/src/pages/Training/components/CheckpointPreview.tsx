import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Info, RefreshCw, Save, X } from 'lucide-react';
import { useAppState } from '../../../hooks/useAppState';
import { useWizardStep } from '../../../hooks/useWizardStep';
import { WizardActions } from './WizardActions';
import { parseApiErrorDetail, parseDatasetId } from '../../../utils/apiParsers';

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
    rowCount: number | null;
}

interface CheckpointSummary {
    dataset_id?: unknown;
    perceptive_field_size?: unknown;
    bet_amount?: unknown;
    initial_capital?: unknown;
}

const RESUME_STEPS = ['Resume Configuration', 'Summary'] as const;

export const CheckpointPreview: React.FC<CheckpointPreviewProps> = ({
    refreshKey = 0,
}) => {
    const { state, dispatch } = useAppState();
    const navigate = useNavigate();
    const { resumeConfig, isTraining } = state.training;
    const [checkpoints, setCheckpoints] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState<string | null>(null);
    const [metadataOpen, setMetadataOpen] = useState(false);
    const [metadataLoading, setMetadataLoading] = useState(false);
    const [metadataError, setMetadataError] = useState<string | null>(null);
    const [metadataPayload, setMetadataPayload] = useState<CheckpointMetadataResponse | null>(null);
    const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
    const [datasetsLoading, setDatasetsLoading] = useState(false);
    const [datasetsError, setDatasetsError] = useState<string | null>(null);
    const [metadataCache, setMetadataCache] = useState<Record<string, CheckpointMetadataResponse>>({});

    const [resumeWizardOpen, setResumeWizardOpen] = useState(false);
    const {
        step: resumeWizardStep,
        isFirstStep: isFirstResumeWizardStep,
        isLastStep: isLastResumeWizardStep,
        goToPreviousStep: goToPreviousResumeWizardStep,
        goToNextStep: goToNextResumeWizardStep,
        resetStep: resetResumeWizardStep,
    } = useWizardStep({ totalSteps: RESUME_STEPS.length });
    const [resumeWizardCheckpoint, setResumeWizardCheckpoint] = useState<string | null>(null);
    const [resumeWizardError, setResumeWizardError] = useState<string | null>(null);
    const [resumeSubmitting, setResumeSubmitting] = useState(false);

    const loadCheckpoints = async () => {
        setLoading(true);
        setError(null);
        setNotice(null);
        try {
            const response = await fetch('/api/training/checkpoints');
            if (!response.ok) {
                throw new Error('Failed to load checkpoints');
            }
            const data = await response.json();
            const checkpointList = Array.isArray(data) ? data : [];
            setCheckpoints(checkpointList);
        } catch {
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
            const response = await fetch('/api/database/roulette-series/datasets/summary');
            if (!response.ok) {
                throw new Error('Failed to load datasets');
            }
            const payload = await response.json();
            const datasetList = Array.isArray(payload?.datasets)
                ? payload.datasets
                    .filter((entry: unknown) => typeof entry === 'object' && entry !== null)
                    .map((entry: { dataset_id?: unknown; dataset_name?: unknown; row_count?: unknown }) => ({
                        datasetId: parseDatasetId(entry.dataset_id),
                        datasetName: typeof entry.dataset_name === 'string' ? entry.dataset_name : '',
                        rowCount: typeof entry.row_count === 'number' ? entry.row_count : null,
                    }))
                    .filter((entry: DatasetInfo) =>
                        entry.datasetId.trim().length > 0 && entry.datasetName.trim().length > 0
                    )
                : [];
            setDatasets(datasetList);
        } catch {
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
        await Promise.all([loadCheckpoints(), loadDatasets()]);
    };

    const handleDelete = async (checkpointName: string) => {
        if (!confirm(`Are you sure you want to delete checkpoint "${checkpointName}"?`)) {
            return;
        }
        setNotice(null);

        try {
            const response = await fetch(`/api/training/checkpoints/${checkpointName}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                throw new Error(parseApiErrorDetail(errorData, 'Failed to delete checkpoint'));
            }

            setCheckpoints((prev) => prev.filter((name) => name !== checkpointName));
        } catch (err) {
            console.error('Error deleting checkpoint:', err);
            setError(`Error deleting checkpoint: ${err instanceof Error ? err.message : String(err)}`);
        }
    };

    const loadCheckpointMetadata = useCallback(async (checkpointName: string) => {
        const response = await fetch(`/api/training/checkpoints/${encodeURIComponent(checkpointName)}/metadata`);
        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(parseApiErrorDetail(errorData, 'Failed to load checkpoint metadata'));
        }
        const payload = (await response.json()) as CheckpointMetadataResponse;
        return payload;
    }, []);

    const cacheCheckpointMetadata = useCallback((checkpointName: string, payload: CheckpointMetadataResponse) => {
        setMetadataCache((prev) => ({ ...prev, [checkpointName]: payload }));
    }, []);

    const prefetchCheckpointMetadata = useCallback(async (checkpointList: string[]) => {
        const toFetch = checkpointList.filter((name) => !metadataCache[name]);
        if (toFetch.length === 0) {
            return;
        }
        const results = await Promise.all(
            toFetch.map(async (name) => {
                try {
                    const payload = await loadCheckpointMetadata(name);
                    return { name, payload };
                } catch {
                    return { name, payload: null };
                }
            })
        );
        results.forEach((result) => {
            if (result.payload) {
                cacheCheckpointMetadata(result.name, result.payload);
            }
        });
    }, [cacheCheckpointMetadata, loadCheckpointMetadata, metadataCache]);

    useEffect(() => {
        if (checkpoints.length === 0) {
            return;
        }
        void prefetchCheckpointMetadata(checkpoints);
    }, [checkpoints, prefetchCheckpointMetadata]);

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
            setResumeWizardError('Training is already in progress.');
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
                const errorPayload = await response.json().catch(() => null);
                setResumeWizardError(`Failed to resume training: ${parseApiErrorDetail(errorPayload, 'Unknown error')}`);
                return;
            }

            dispatch({ type: 'SET_TRAINING_IS_TRAINING', payload: true });
            closeResumeWizard();
        } catch {
            setResumeWizardError('Failed to connect to training server');
        } finally {
            setResumeSubmitting(false);
        }
    };

    const parsePositiveNumber = (value: unknown): number | null => {
        if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) {
            return null;
        }
        return value;
    };

    const handleEvaluateCheckpoint = async (checkpointName: string) => {
        setNotice(null);
        try {
            const payload = metadataCache[checkpointName] ?? await loadCheckpointMetadata(checkpointName);
            if (!metadataCache[checkpointName]) {
                cacheCheckpointMetadata(checkpointName, payload);
            }
            const summary = (payload.summary || {}) as CheckpointSummary;
            const requiredRows = parsePositiveNumber(summary.perceptive_field_size);
            const preferredDatasetId = parseDatasetId(summary.dataset_id);
            const compatibleDatasets = datasets.filter((dataset) => (
                requiredRows === null || dataset.rowCount === null || dataset.rowCount >= requiredRows
            ));
            const selectedDataset = (
                compatibleDatasets.find((dataset) => dataset.datasetId === preferredDatasetId)
                ?? compatibleDatasets[0]
            );

            if (!selectedDataset) {
                setError('No compatible dataset is available for this checkpoint.');
                return;
            }

            const betAmount = parsePositiveNumber(summary.bet_amount) ?? 1;
            const initialCapital = parsePositiveNumber(summary.initial_capital) ?? 100;

            dispatch({ type: 'RESET_INFERENCE_SESSION' });
            dispatch({
                type: 'SET_INFERENCE_SETUP',
                payload: {
                    checkpoint: checkpointName,
                    selectedDataset: selectedDataset.datasetId,
                    datasetSource: 'source',
                    uploadedDatasetName: null,
                    datasetFileMetadata: null,
                    initialCapital: Number(initialCapital),
                    betAmount: Number(betAmount),
                },
            });
            dispatch({
                type: 'SET_INFERENCE_SESSION_STATE',
                payload: {
                    isActive: false,
                    currentCapital: Number(initialCapital),
                    currentBet: Number(betAmount),
                    lastPrediction: null,
                    totalSteps: 0,
                },
            });
            navigate('/inference');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unable to start evaluation.');
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
            setError('Training is already in progress.');
            return;
        }
        setResumeWizardOpen(true);
        resetResumeWizardStep();
        setResumeWizardError(null);
        setResumeWizardCheckpoint(checkpointName);
        dispatch({ type: 'SET_TRAINING_RESUME_CONFIG', payload: { selectedCheckpoint: checkpointName } });

        if (!metadataCache[checkpointName]) {
            try {
                const payload = await loadCheckpointMetadata(checkpointName);
                cacheCheckpointMetadata(checkpointName, payload);
            } catch {
                setResumeWizardError('Unable to load checkpoint metadata.');
            }
        }
    };

    const closeResumeWizard = () => {
        if (resumeSubmitting) {
            return;
        }
        setResumeWizardOpen(false);
        resetResumeWizardStep();
        setResumeWizardCheckpoint(null);
        setResumeWizardError(null);
    };

    const handleResumeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        dispatch({
            type: 'SET_TRAINING_RESUME_CONFIG',
            payload: { numAdditionalEpisodes: Number(event.target.value) },
        });
    };

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
                {notice && <div className="preview-notice">{notice}</div>}
                {!loading && !error && checkpoints.length === 0 && (
                    <div className="preview-empty">No checkpoints available</div>
                )}
                {!loading && !error && datasetsError && (
                    <div className="preview-error">{datasetsError}</div>
                )}
                {!loading && !error && checkpoints.length > 0 && (
                    <div className="preview-list">
                        {checkpoints.map((name) => {
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
                                        <button
                                            className="preview-row-icon preview-row-icon-resume"
                                            onClick={() => openResumeWizard(name)}
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
                                                ? String(row.value)
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
                    <div
                        className="wizard-modal"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="resume-training-wizard-title"
                    >
                        <div className="wizard-modal-header">
                            <div id="resume-training-wizard-title" className="wizard-modal-title">
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
                                                    ? String(row.value)
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
                        <WizardActions
                            isFirstStep={isFirstResumeWizardStep}
                            isLastStep={isLastResumeWizardStep}
                            isSubmitting={resumeSubmitting}
                            onCancel={closeResumeWizard}
                            onPrevious={goToPreviousResumeWizardStep}
                            onNext={goToNextResumeWizardStep}
                            onConfirm={handleResumeTraining}
                        />
                    </div>
                </div>
            )}
        </div>
    );
};

