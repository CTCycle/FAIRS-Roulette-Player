import React, { useEffect, useMemo, useState } from 'react';
import { Check, ChevronLeft, ChevronRight, Database, Play, X } from 'lucide-react';
import { useAppState } from '../../../context/AppStateContext';
import { buildTrainingPayload } from './trainingPayload';

interface DatasetPreviewProps {
    refreshKey: number;
    onDelete?: () => void;
}

interface DatasetSummary {
    name: string;
    rowCount: number | null;
}

type WizardStep = 0 | 1 | 2 | 3 | 4;

const WIZARD_STEPS = [
    'Agent Configuration',
    'Environment & Memory',
    'Dataset Configuration',
    'Session & Compute',
    'Summary',
] as const;

export const DatasetPreview: React.FC<DatasetPreviewProps> = ({
    refreshKey,
    onDelete,
}) => {
    const { state, dispatch } = useAppState();
    const { newConfig, isTraining } = state.training;
    const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [wizardOpen, setWizardOpen] = useState(false);
    const [wizardStep, setWizardStep] = useState<WizardStep>(0);
    const [wizardDataset, setWizardDataset] = useState<string | null>(null);
    const [wizardError, setWizardError] = useState<string | null>(null);
    const [wizardSubmitting, setWizardSubmitting] = useState(false);

    const loadDatasets = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/database/roulette-series/datasets/summary');
            if (!response.ok) {
                throw new Error('Failed to load dataset summary');
            }
            const data = await response.json();
            const datasetList = Array.isArray(data?.datasets)
                ? data.datasets
                    .filter((entry: unknown) => typeof entry === 'object' && entry !== null)
                    .map((entry: { dataset_name?: unknown; row_count?: unknown }) => ({
                        name: typeof entry.dataset_name === 'string' ? entry.dataset_name : '',
                        rowCount: typeof entry.row_count === 'number' ? entry.row_count : null,
                    }))
                    .filter((entry: DatasetSummary) => entry.name.trim().length > 0)
                : [];
            setDatasets(datasetList);
        } catch (err) {
            try {
                const fallbackResponse = await fetch('/api/database/roulette-series/datasets');
                if (!fallbackResponse.ok) {
                    throw new Error('Failed to load datasets');
                }
                const fallbackData = await fallbackResponse.json();
                const fallbackList = Array.isArray(fallbackData?.datasets)
                    ? fallbackData.datasets
                        .filter((name: unknown) => typeof name === 'string' && name.trim().length > 0)
                        .map((name: string) => ({ name, rowCount: null }))
                    : [];
                setDatasets(fallbackList);
                setError(null);
            } catch (fallbackError) {
                setError('Unable to load datasets.');
                setDatasets([]);
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void loadDatasets();
    }, [refreshKey]);

    const updateNewConfig = (updates: Partial<typeof newConfig>) => {
        dispatch({ type: 'SET_TRAINING_NEW_CONFIG', payload: updates });
    };

    const handleInputChange = (
        event: React.ChangeEvent<HTMLInputElement>,
    ) => {
        const { name, value, type, checked } = event.target;
        if (type === 'checkbox') {
            updateNewConfig({ [name]: checked } as Partial<typeof newConfig>);
            return;
        }
        updateNewConfig({ [name]: value } as Partial<typeof newConfig>);
    };

    const handleNumberChange = (name: keyof typeof newConfig, value: number) => {
        updateNewConfig({ [name]: value } as Partial<typeof newConfig>);
    };

    const handleDelete = async (datasetName: string) => {
        try {
            const response = await fetch(`/api/database/roulette-series/datasets/${encodeURIComponent(datasetName)}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                throw new Error('Failed to delete dataset');
            }
            await loadDatasets();
            onDelete?.();
        } catch (err) {
            setError('Failed to delete dataset.');
        }
    };

    const openWizard = (datasetName: string) => {
        if (isTraining) {
            alert('Training is already in progress.');
            return;
        }
        setWizardDataset(datasetName);
        setWizardStep(0);
        setWizardError(null);
        setWizardOpen(true);
    };

    const closeWizard = () => {
        if (wizardSubmitting) {
            return;
        }
        setWizardOpen(false);
        setWizardDataset(null);
        setWizardStep(0);
        setWizardError(null);
    };

    const handleStartTraining = async () => {
        if (isTraining) {
            alert('Training is already in progress.');
            return;
        }
        if (!wizardDataset) {
            setWizardError('Select a dataset to continue.');
            return;
        }

        const config = buildTrainingPayload(newConfig, wizardDataset);
        setWizardSubmitting(true);
        setWizardError(null);

        try {
            const response = await fetch('/api/training/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config),
            });

            if (!response.ok) {
                const errorPayload = await response.json();
                setWizardError(`Failed to start training: ${errorPayload.detail || 'Unknown error'}`);
                return;
            }

            dispatch({ type: 'SET_TRAINING_IS_TRAINING', payload: true });
            closeWizard();
        } catch (err) {
            setWizardError('Failed to connect to training server');
        } finally {
            setWizardSubmitting(false);
        }
    };

    const formatRowCount = (rowCount: number | null) => {
        if (rowCount === null) {
            return 'Rows: --';
        }
        return `${rowCount.toLocaleString()} rows`;
    };

    const sampleSizeValue = Number(newConfig.trainSampleSize);
    const validationValue = Number(newConfig.validationSize);

    const summaryRows = useMemo(() => ([
        { label: 'Dataset', value: wizardDataset ?? '-' },
        { label: 'Perceptive Field', value: newConfig.perceptiveField },
        { label: 'QNet Neurons', value: newConfig.numNeurons },
        { label: 'Embedding Dims', value: newConfig.embeddingDims },
        { label: 'Update Freq', value: newConfig.modelUpdateFreq },
        { label: 'Explore Rate', value: newConfig.explorationRate },
        { label: 'Decay', value: newConfig.explorationRateDecay },
        { label: 'Min Explore Rate', value: newConfig.minExplorationRate },
        { label: 'Discount Rate', value: newConfig.discountRate },
        { label: 'Bet Amount', value: newConfig.betAmount },
        { label: 'Initial Capital', value: newConfig.initialCapital },
        { label: 'Max Memory', value: newConfig.maxMemorySize },
        { label: 'Replay Buffer', value: newConfig.replayBufferSize },
        { label: 'Sample Size', value: sampleSizeValue },
        { label: 'Validation Split', value: validationValue },
        { label: 'Split Seed', value: newConfig.splitSeed },
        { label: 'Episodes', value: newConfig.episodes },
        { label: 'Max Steps', value: newConfig.maxStepsEpisode },
        { label: 'Batch Size', value: newConfig.batchSize },
        { label: 'Learning Rate', value: newConfig.learningRate },
        { label: 'Training Seed', value: newConfig.trainingSeed },
        { label: 'Workers', value: newConfig.numWorkers },
        { label: 'Save Checkpoints', value: newConfig.saveCheckpoints ? 'Yes' : 'No' },
        { label: 'Checkpoints Frequency', value: newConfig.checkpointsFreq },
        { label: 'Use GPU', value: newConfig.deviceGPU ? 'Yes' : 'No' },
        { label: 'Mixed Precision', value: newConfig.useMixedPrecision ? 'Yes' : 'No' },
    ]), [
        newConfig,
        sampleSizeValue,
        validationValue,
        wizardDataset,
    ]);

    return (
        <div className="dataset-preview">
            <div className="preview-header">
                <Database size={18} />
                <span>Available Datasets</span>
            </div>
            <div className="preview-content">
                {loading && <div className="preview-loading">Loading...</div>}
                {error && <div className="preview-error">{error}</div>}
                {!loading && !error && datasets.length === 0 && (
                    <div className="preview-empty">No datasets available</div>
                )}
                {!loading && !error && datasets.length > 0 && (
                    <div className="preview-list">
                        {datasets.slice(0, 6).map((dataset) => (
                            <div key={dataset.name} className="preview-row">
                                <span className="preview-row-name">{dataset.name}</span>
                                <span className="preview-row-spacer" />
                                <span className="preview-row-count">{formatRowCount(dataset.rowCount)}</span>
                                <button
                                    className="preview-row-icon preview-row-icon-start"
                                    onClick={() => openWizard(dataset.name)}
                                    title="Configure training with this dataset"
                                    disabled={isTraining}
                                >
                                    <Play size={16} />
                                </button>
                                <button
                                    className="preview-row-delete"
                                    onClick={() => handleDelete(dataset.name)}
                                    title="Remove dataset"
                                >
                                    <X size={16} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {wizardOpen && (
                <div className="wizard-modal-overlay">
                    <div className="wizard-modal" role="dialog" aria-modal="true">
                        <div className="wizard-modal-header">
                            <div className="wizard-modal-title">
                                <Play size={18} />
                                New Training Wizard
                            </div>
                            <button className="wizard-modal-close" onClick={closeWizard} title="Close">
                                <X size={16} />
                            </button>
                        </div>
                        <div className="wizard-modal-subtitle">
                            <span>Dataset: {wizardDataset}</span>
                            <span>{`Step ${wizardStep + 1} of ${WIZARD_STEPS.length}`}</span>
                        </div>
                        <div className="wizard-step-title">{WIZARD_STEPS[wizardStep]}</div>
                        <div className="wizard-step-content">
                            {wizardStep === 0 && (
                                <div className="wizard-grid wizard-grid-2x4">
                                    <div className="form-group">
                                        <label className="form-label">Perceptive Field</label>
                                        <input type="number" name="perceptiveField" value={newConfig.perceptiveField} onChange={handleInputChange} className="form-input" max="1024" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">QNet Neurons</label>
                                        <input type="number" name="numNeurons" value={newConfig.numNeurons} onChange={handleInputChange} className="form-input" max="10000" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Embedding Dims</label>
                                        <input type="number" name="embeddingDims" value={newConfig.embeddingDims} onChange={handleInputChange} className="form-input" step="8" max="9999" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Update Freq</label>
                                        <input type="number" name="modelUpdateFreq" value={newConfig.modelUpdateFreq} onChange={handleInputChange} className="form-input" max="1000" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Explore Rate</label>
                                        <input type="number" name="explorationRate" value={newConfig.explorationRate} onChange={handleInputChange} className="form-input" step="0.01" max="1.0" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Decay</label>
                                        <input type="number" name="explorationRateDecay" value={newConfig.explorationRateDecay} onChange={handleInputChange} className="form-input" step="0.001" max="1.0" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Min Explore Rate</label>
                                        <input type="number" name="minExplorationRate" value={newConfig.minExplorationRate} onChange={handleInputChange} className="form-input" step="0.01" max="1.0" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Discount Rate</label>
                                        <input type="number" name="discountRate" value={newConfig.discountRate} onChange={handleInputChange} className="form-input" step="0.01" max="1.0" />
                                    </div>
                                </div>
                            )}

                            {wizardStep === 1 && (
                                <div className="wizard-grid wizard-grid-2x2">
                                    <div className="form-group">
                                        <label className="form-label">Bet Amount</label>
                                        <input type="number" name="betAmount" value={newConfig.betAmount} onChange={handleInputChange} className="form-input" min="1" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Initial Capital</label>
                                        <input type="number" name="initialCapital" value={newConfig.initialCapital} onChange={handleInputChange} className="form-input" min="1" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Max Memory</label>
                                        <input type="number" name="maxMemorySize" value={newConfig.maxMemorySize} onChange={handleInputChange} className="form-input" min="100" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Replay Buffer</label>
                                        <input type="number" name="replayBufferSize" value={newConfig.replayBufferSize} onChange={handleInputChange} className="form-input" min="100" />
                                    </div>
                                </div>
                            )}

                            {wizardStep === 2 && (
                                <div className="wizard-stack">
                                    <div className="form-group">
                                        <label className="form-label">Sample Size</label>
                                        <div className="wizard-slider">
                                            <input
                                                type="range"
                                                min="0.01"
                                                max="1"
                                                step="0.01"
                                                value={sampleSizeValue}
                                                onChange={(event) => handleNumberChange('trainSampleSize', Number(event.target.value))}
                                            />
                                            <span>{sampleSizeValue.toFixed(2)}</span>
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Validation Split</label>
                                        <div className="wizard-slider">
                                            <input
                                                type="range"
                                                min="0"
                                                max="0.99"
                                                step="0.01"
                                                value={validationValue}
                                                onChange={(event) => handleNumberChange('validationSize', Number(event.target.value))}
                                            />
                                            <span>{validationValue.toFixed(2)}</span>
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Split Seed</label>
                                        <input type="number" name="splitSeed" value={newConfig.splitSeed} onChange={handleInputChange} className="form-input" />
                                    </div>
                                </div>
                            )}

                            {wizardStep === 3 && (
                                <div className="wizard-session-compute">
                                    <div className="wizard-grid wizard-grid-3x2">
                                        <div className="form-group">
                                            <label className="form-label">Episodes</label>
                                            <input type="number" name="episodes" value={newConfig.episodes} onChange={handleInputChange} className="form-input" min="1" />
                                        </div>
                                        <div className="form-group">
                                            <label className="form-label">Max Steps</label>
                                            <input type="number" name="maxStepsEpisode" value={newConfig.maxStepsEpisode} onChange={handleInputChange} className="form-input" min="100" />
                                        </div>
                                        <div className="form-group">
                                            <label className="form-label">Batch Size</label>
                                            <input type="number" name="batchSize" value={newConfig.batchSize} onChange={handleInputChange} className="form-input" min="1" />
                                        </div>
                                        <div className="form-group">
                                            <label className="form-label">Learning Rate</label>
                                            <input type="number" name="learningRate" value={newConfig.learningRate} onChange={handleInputChange} className="form-input" step="0.0001" min="0" />
                                        </div>
                                        <div className="form-group">
                                            <label className="form-label">Training Seed</label>
                                            <input type="number" name="trainingSeed" value={newConfig.trainingSeed} onChange={handleInputChange} className="form-input" />
                                        </div>
                                        <div className="form-group">
                                            <label className="form-label">Workers</label>
                                            <input type="number" name="numWorkers" value={newConfig.numWorkers} onChange={handleInputChange} className="form-input" min="0" />
                                            <div className="wizard-inline">
                                                <label className="checkbox-visual">
                                                    <input type="checkbox" name="saveCheckpoints" checked={newConfig.saveCheckpoints} onChange={handleInputChange} />
                                                    <span>Save checkpoints every</span>
                                                </label>
                                                <input
                                                    type="number"
                                                    name="checkpointsFreq"
                                                    value={newConfig.checkpointsFreq}
                                                    onChange={handleInputChange}
                                                    className="form-input inline-input-sm"
                                                    min="1"
                                                    disabled={!newConfig.saveCheckpoints}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                    <div className="wizard-checkboxes">
                                        <label className="checkbox-visual">
                                            <input type="checkbox" name="deviceGPU" checked={newConfig.deviceGPU} onChange={handleInputChange} />
                                            <span>Use GPU</span>
                                        </label>
                                        <label className="checkbox-visual">
                                            <input type="checkbox" name="useMixedPrecision" checked={newConfig.useMixedPrecision} onChange={handleInputChange} />
                                            <span>Mixed Precision</span>
                                        </label>
                                    </div>
                                </div>
                            )}

                            {wizardStep === 4 && (
                                <div className="wizard-summary">
                                    {summaryRows.map((row) => (
                                        <div key={row.label} className="wizard-summary-row">
                                            <span className="wizard-summary-label">{row.label}</span>
                                            <span className="wizard-summary-value">
                                                {typeof row.value === 'number' ? row.value.toLocaleString() : String(row.value)}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {wizardError && (
                            <div className="wizard-error">{wizardError}</div>
                        )}

                        <div className="wizard-actions">
                            <button
                                type="button"
                                className="wizard-btn wizard-btn-secondary"
                                onClick={closeWizard}
                                disabled={wizardSubmitting}
                            >
                                Cancel
                            </button>
                            <div className="wizard-actions-right">
                                <button
                                    type="button"
                                    className="wizard-btn wizard-btn-secondary"
                                    onClick={() => setWizardStep((prev) => Math.max(0, prev - 1) as WizardStep)}
                                    disabled={wizardStep === 0 || wizardSubmitting}
                                >
                                    <ChevronLeft size={16} />
                                    Previous
                                </button>
                                {wizardStep < WIZARD_STEPS.length - 1 ? (
                                    <button
                                        type="button"
                                        className="wizard-btn wizard-btn-primary"
                                        onClick={() => setWizardStep((prev) => Math.min(WIZARD_STEPS.length - 1, prev + 1) as WizardStep)}
                                        disabled={wizardSubmitting}
                                    >
                                        Next
                                        <ChevronRight size={16} />
                                    </button>
                                ) : (
                                    <button
                                        type="button"
                                        className="wizard-btn wizard-btn-primary"
                                        onClick={handleStartTraining}
                                        disabled={wizardSubmitting}
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
