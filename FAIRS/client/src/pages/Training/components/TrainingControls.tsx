import React, { useEffect, useState } from 'react';
import { Settings, Play, RefreshCw, Cpu, Layers, Activity, Database, ChevronsDown, ChevronsRight } from 'lucide-react';
import type { TrainingNewConfig, TrainingResumeConfig } from '../../../context/AppStateContext';

interface TrainingControlsProps {
    newConfig: TrainingNewConfig;
    resumeConfig: TrainingResumeConfig;
    onNewConfigChange: (updates: Partial<TrainingNewConfig>) => void;
    onResumeConfigChange: (updates: Partial<TrainingResumeConfig>) => void;
    datasetRefreshKey: number;
}

export const TrainingControls: React.FC<TrainingControlsProps> = ({
    newConfig,
    resumeConfig,
    onNewConfigChange,
    onResumeConfigChange,
    datasetRefreshKey,
}) => {
    const [activeSection, setActiveSection] = useState<'new' | 'resume' | null>('new');
    const [datasetOptions, setDatasetOptions] = useState<string[]>([]);
    const [datasetError, setDatasetError] = useState<string | null>(null);
    const [datasetLoading, setDatasetLoading] = useState(false);
    const [checkpointOptions, setCheckpointOptions] = useState<string[]>([]);
    const [checkpointsLoading, setCheckpointsLoading] = useState(false);
    const [checkpointsError, setCheckpointsError] = useState<string | null>(null);

    const handleNewChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        if (e.target instanceof HTMLInputElement && e.target.type === 'checkbox') {
            onNewConfigChange({
                [name]: e.target.checked
            } as Partial<TrainingNewConfig>);
            return;
        }
        onNewConfigChange({
            [name]: value
        } as Partial<TrainingNewConfig>);
    };

    const handleResumeChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        if (name === 'selectedCheckpoint') {
            onResumeConfigChange({ selectedCheckpoint: value });
            return;
        }
        onResumeConfigChange({
            [name]: Number(value)
        } as Partial<TrainingResumeConfig>);
    };

    const loadDatasetOptions = async () => {
        setDatasetLoading(true);
        try {
            const response = await fetch('/api/database/roulette-series/datasets');
            if (!response.ok) {
                throw new Error('Failed to load datasets');
            }
            const data = await response.json();
            const datasets = Array.isArray(data?.datasets)
                ? data.datasets.filter((name: unknown) => typeof name === 'string' && name.trim().length > 0)
                : [];
            setDatasetOptions(datasets);
            if (newConfig.datasetName && !datasets.includes(newConfig.datasetName)) {
                onNewConfigChange({ datasetName: '' });
            }
            setDatasetError(null);
        } catch (err) {
            setDatasetOptions([]);
            setDatasetError('Unable to load dataset names.');
        } finally {
            setDatasetLoading(false);
        }
    };

    useEffect(() => {
        void loadDatasetOptions();
    }, [datasetRefreshKey]);

    const loadCheckpointOptions = async () => {
        setCheckpointsLoading(true);
        try {
            const response = await fetch('/api/training/checkpoints');
            if (!response.ok) {
                throw new Error('Failed to load checkpoints');
            }
            const data = await response.json();
            const checkpoints = Array.isArray(data) ? data : [];
            setCheckpointOptions(checkpoints);
            if (resumeConfig.selectedCheckpoint && !checkpoints.includes(resumeConfig.selectedCheckpoint)) {
                onResumeConfigChange({ selectedCheckpoint: '' });
            }
            setCheckpointsError(null);
        } catch (err) {
            setCheckpointOptions([]);
            setCheckpointsError('Unable to load checkpoints.');
        } finally {
            setCheckpointsLoading(false);
        }
    };

    useEffect(() => {
        if (activeSection === 'resume') {
            void loadCheckpointOptions();
        }
    }, [activeSection]);

    const toggleSection = (section: 'new' | 'resume') => {
        setActiveSection(activeSection === section ? null : section);
    };

    return (
        <div className="card controls-section">
            <div className="card-header">
                <h2 className="card-title">
                    <Settings size={24} />
                    Training Configuration
                </h2>
            </div>

            <div className="training-accordions">
                {/* NEW TRAINING SESSION */}
                <div className={`training-accordion ${activeSection === 'new' ? 'expanded' : ''}`}>
                    <div
                        className="training-accordion-summary"
                        onClick={() => toggleSection('new')}
                    >
                        <span className="training-accordion-title">
                            <Play size={18} /> New Training Session
                        </span>
                        {activeSection === 'new' ? <ChevronsDown size={18} /> : <ChevronsRight size={18} />}
                    </div>
                    {activeSection === 'new' && (
                        <div className="training-accordion-content">
                            <form onSubmit={(event) => event.preventDefault()}>
                                {/* === AGENT CONFIGURATION + ENVIRONMENT/MEMORY (Side-by-Side) === */}
                                <div className="controls-row-side-by-side">
                                    {/* Agent Configuration (Left, 70%) */}
                                    <fieldset className="control-fieldset control-fieldset-left">
                                        <legend className="control-legend">
                                            <Activity size={16} className="text-blue-500" /> Agent Configuration
                                        </legend>
                                        {/* Upper 2x2 grid */}
                                        <div className="training-grid-2x2">
                                            <div className="form-group">
                                                <label className="form-label">Perceptive Field</label>
                                                <input type="number" name="perceptiveField" value={newConfig.perceptiveField} onChange={handleNewChange} className="form-input" max="1024" />
                                            </div>
                                            <div className="form-group">
                                                <label className="form-label">QNet Neurons</label>
                                                <input type="number" name="numNeurons" value={newConfig.numNeurons} onChange={handleNewChange} className="form-input" max="10000" />
                                            </div>
                                            <div className="form-group">
                                                <label className="form-label">Embedding Dims</label>
                                                <input type="number" name="embeddingDims" value={newConfig.embeddingDims} onChange={handleNewChange} className="form-input" step="8" max="9999" />
                                            </div>
                                            <div className="form-group">
                                                <label className="form-label">Update Freq</label>
                                                <input type="number" name="modelUpdateFreq" value={newConfig.modelUpdateFreq} onChange={handleNewChange} className="form-input" max="1000" />
                                            </div>
                                        </div>
                                        <hr className="fieldset-separator-horizontal" />
                                        {/* Lower 2x2 grid */}
                                        <div className="training-grid-2x2">
                                            <div className="form-group">
                                                <label className="form-label">Explore Rate</label>
                                                <input type="number" name="explorationRate" value={newConfig.explorationRate} onChange={handleNewChange} className="form-input" step="0.01" max="1.0" />
                                            </div>
                                            <div className="form-group">
                                                <label className="form-label">Decay</label>
                                                <input type="number" name="explorationRateDecay" value={newConfig.explorationRateDecay} onChange={handleNewChange} className="form-input" step="0.001" max="1.0" />
                                            </div>
                                            <div className="form-group">
                                                <label className="form-label">Min Explore Rate</label>
                                                <input type="number" name="minExplorationRate" value={newConfig.minExplorationRate} onChange={handleNewChange} className="form-input" step="0.01" max="1.0" />
                                            </div>
                                            <div className="form-group">
                                                <label className="form-label">Discount Rate</label>
                                                <input type="number" name="discountRate" value={newConfig.discountRate} onChange={handleNewChange} className="form-input" step="0.01" max="1.0" />
                                            </div>
                                        </div>
                                    </fieldset>

                                    {/* Environment & Memory (Right, 30%) */}
                                    <fieldset className="control-fieldset control-fieldset-right">
                                        <legend className="control-legend">
                                            <Layers size={16} /> Environment & Memory
                                        </legend>
                                        <div className="training-stack-vertical">
                                            <div className="form-group">
                                                <label className="form-label">Bet Amount</label>
                                                <input type="number" name="betAmount" value={newConfig.betAmount} onChange={handleNewChange} className="form-input" min="1" />
                                            </div>
                                            <div className="form-group">
                                                <label className="form-label">Initial Capital</label>
                                                <input type="number" name="initialCapital" value={newConfig.initialCapital} onChange={handleNewChange} className="form-input" min="1" />
                                            </div>
                                            <div className="form-group">
                                                <label className="form-label">Max Memory</label>
                                                <input type="number" name="maxMemorySize" value={newConfig.maxMemorySize} onChange={handleNewChange} className="form-input" min="100" />
                                            </div>
                                            <div className="form-group">
                                                <label className="form-label">Replay Buffer</label>
                                                <input type="number" name="replayBufferSize" value={newConfig.replayBufferSize} onChange={handleNewChange} className="form-input" min="100" />
                                            </div>
                                        </div>
                                    </fieldset>
                                </div>

                                {/* === DATASET === */}
                                <fieldset className="control-fieldset">
                                    <legend className="control-legend">
                                        <Database size={16} /> Dataset Configuration
                                    </legend>
                                    <div className="controls-two-column">
                                        {/* Left column - Database Selection & Splits (70%) */}
                                        <div className="controls-column-left" style={{ flex: 7 }}>
                                            <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                                                <label className="form-label">Training Dataset</label>
                                                <select
                                                    name="datasetName"
                                                    value={newConfig.datasetName}
                                                    onChange={handleNewChange}
                                                    className="form-select"
                                                    disabled={datasetLoading}
                                                >
                                                    {datasetOptions.length === 0 ? (
                                                        <option value="">No data available</option>
                                                    ) : (
                                                        <>
                                                            <option value="">All datasets</option>
                                                            {datasetOptions.map((dataset) => (
                                                                <option key={dataset} value={dataset}>
                                                                    {dataset}
                                                                </option>
                                                            ))}
                                                        </>
                                                    )}
                                                </select>
                                                {datasetError && (
                                                    <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#dc2626' }}>
                                                        {datasetError}
                                                    </div>
                                                )}
                                            </div>
                                            <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                                                <label className="form-label">Train / Validation Split</label>
                                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                                                    <input type="number" name="trainSampleSize" value={newConfig.trainSampleSize} onChange={handleNewChange} className="form-input" step="0.05" placeholder="Train %" title="Training Sample Size" />
                                                    <input type="number" name="validationSize" value={newConfig.validationSize} onChange={handleNewChange} className="form-input" step="0.05" placeholder="Val %" title="Validation Size" />
                                                </div>
                                            </div>
                                            <div className="form-group">
                                                <label className="form-label">Split Seed</label>
                                                <input type="number" name="splitSeed" value={newConfig.splitSeed} onChange={handleNewChange} className="form-input" />
                                            </div>
                                        </div>

                                        {/* Vertical Separator */}
                                        <div className="fieldset-separator-vertical" />

                                        {/* Right column - Generator Toggles (30%) */}
                                        <div className="controls-column-right" style={{ flex: 3 }}>
                                            <div style={{
                                                display: 'flex',
                                                flexDirection: 'column',
                                                gap: '0.75rem',
                                                padding: '0.75rem',
                                                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                                                borderRadius: '6px',
                                                border: '1px solid rgba(255, 255, 255, 0.05)',
                                                height: '100%'
                                            }}>
                                                {/* Data Generator Toggle */}
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                                                    <label className="checkbox-visual" style={{ marginBottom: 0 }}>
                                                        <input type="checkbox" name="useDataGen" checked={newConfig.useDataGen} onChange={handleNewChange} />
                                                        <span style={{ fontWeight: 500 }}>Synthetic generator</span>
                                                    </label>
                                                    <div className="inline-input-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: newConfig.useDataGen ? 1 : 0.5 }}>
                                                        <input type="number" name="numGeneratedSamples" value={newConfig.numGeneratedSamples} onChange={handleNewChange} className="form-input inline-input-sm" disabled={!newConfig.useDataGen} />
                                                        <span style={{ fontSize: '0.8rem', color: '#64748b' }}>samples</span>
                                                    </div>
                                                </div>

                                                {/* Shuffle Toggle */}
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                                                    <label className="checkbox-visual" style={{ marginBottom: 0 }}>
                                                        <input type="checkbox" name="setShuffle" checked={newConfig.setShuffle} onChange={handleNewChange} />
                                                        <span style={{ fontWeight: 500 }}>Shuffle buffer</span>
                                                    </label>
                                                    <div className="inline-input-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: newConfig.setShuffle ? 1 : 0.5 }}>
                                                        <input type="number" name="shuffleSize" value={newConfig.shuffleSize} onChange={handleNewChange} className="form-input inline-input-sm" disabled={!newConfig.setShuffle} />
                                                        <span style={{ fontSize: '0.8rem', color: '#64748b' }}>size</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </fieldset>


                                {/* === SESSION & COMPUTE === */}
                                <fieldset className="control-fieldset">
                                    <legend className="control-legend">
                                        <Cpu size={16} /> Session & Compute
                                    </legend>
                                    <div className="session-compute-layout">
                                        {/* Left side - 2x3 Grid of inputs */}
                                        <div className="session-compute-left">
                                            <div className="training-grid-2x3">
                                                <div className="form-group">
                                                    <label className="form-label">Episodes</label>
                                                    <input type="number" name="episodes" value={newConfig.episodes} onChange={handleNewChange} className="form-input" min="1" />
                                                </div>
                                                <div className="form-group">
                                                    <label className="form-label">Max Steps</label>
                                                    <input type="number" name="maxStepsEpisode" value={newConfig.maxStepsEpisode} onChange={handleNewChange} className="form-input" min="100" />
                                                </div>
                                                <div className="form-group">
                                                    <label className="form-label">Batch Size</label>
                                                    <input type="number" name="batchSize" value={newConfig.batchSize} onChange={handleNewChange} className="form-input" min="1" />
                                                </div>
                                                <div className="form-group">
                                                    <label className="form-label">Learning Rate</label>
                                                    <input type="number" name="learningRate" value={newConfig.learningRate} onChange={handleNewChange} className="form-input" step="0.0001" min="0" />
                                                </div>
                                                <div className="form-group">
                                                    <label className="form-label">Training Seed</label>
                                                    <input type="number" name="trainingSeed" value={newConfig.trainingSeed} onChange={handleNewChange} className="form-input" />
                                                </div>
                                                <div className="form-group">
                                                    <label className="form-label">Workers</label>
                                                    <input type="number" name="numWorkers" value={newConfig.numWorkers} onChange={handleNewChange} className="form-input" min="0" />
                                                </div>
                                            </div>
                                        </div>

                                        {/* Right side - Checkbox sections stacked vertically */}
                                        <div className="session-compute-right">
                                            {/* Hardware Acceleration */}
                                            <div style={{
                                                padding: '0.75rem',
                                                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                                                borderRadius: '6px',
                                                border: '1px solid rgba(255, 255, 255, 0.05)'
                                            }}>
                                                <h4 style={{
                                                    fontSize: '0.8rem',
                                                    fontWeight: 600,
                                                    color: '#94a3b8',
                                                    marginBottom: '0.5rem',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.05em'
                                                }}>Hardware Acceleration</h4>
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                                                        <label className="checkbox-visual" style={{ marginBottom: 0 }}>
                                                            <input type="checkbox" name="deviceGPU" checked={newConfig.deviceGPU} onChange={handleNewChange} />
                                                            <span>Use GPU</span>
                                                        </label>
                                                        <div className="inline-input-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: newConfig.deviceGPU ? 1 : 0.5 }}>
                                                            <input type="number" name="deviceID" value={newConfig.deviceID} onChange={handleNewChange} className="form-input inline-input-sm" placeholder="ID" disabled={!newConfig.deviceGPU} />
                                                        </div>
                                                    </div>
                                                    <label className="checkbox-visual">
                                                        <input type="checkbox" name="useMixedPrecision" checked={newConfig.useMixedPrecision} onChange={handleNewChange} />
                                                        <span>Mixed Precision</span>
                                                    </label>
                                                </div>
                                            </div>

                                            {/* Monitoring & Persistence */}
                                            <div style={{
                                                padding: '0.75rem',
                                                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                                                borderRadius: '6px',
                                                border: '1px solid rgba(255, 255, 255, 0.05)'
                                            }}>
                                                <h4 style={{
                                                    fontSize: '0.8rem',
                                                    fontWeight: 600,
                                                    color: '#94a3b8',
                                                    marginBottom: '0.5rem',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.05em'
                                                }}>Monitoring & Persistence</h4>
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                                    <label className="checkbox-visual">
                                                        <input type="checkbox" name="useTensorboard" checked={newConfig.useTensorboard} onChange={handleNewChange} />
                                                        <span>Enable TensorBoard</span>
                                                    </label>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                                                        <label className="checkbox-visual" style={{ marginBottom: 0 }}>
                                                            <input type="checkbox" name="saveCheckpoints" checked={newConfig.saveCheckpoints} onChange={handleNewChange} />
                                                            <span>Save Checkpoints</span>
                                                        </label>
                                                        <div className="inline-input-group" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', opacity: newConfig.saveCheckpoints ? 1 : 0.5 }}>
                                                            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>every</span>
                                                            <input type="number" name="checkpointsFreq" value={newConfig.checkpointsFreq} onChange={handleNewChange} className="form-input inline-input-sm" disabled={!newConfig.saveCheckpoints} />
                                                            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>ep.</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </fieldset>

                                <div className="form-actions">
                                    <button type="button" className="btn-primary btn-narrow" disabled title="Use the dataset preview to start training">
                                        <Play size={18} /> Use dataset preview to start
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}
                </div>

                {/* RESUME TRAINING SESSION */}
                <div className={`training-accordion ${activeSection === 'resume' ? 'expanded' : ''}`}>
                    <div
                        className="training-accordion-summary"
                        onClick={() => toggleSection('resume')}
                    >
                        <span className="training-accordion-title">
                            <RefreshCw size={18} /> Resume Training Session
                        </span>
                        {activeSection === 'resume' ? <ChevronsDown size={18} /> : <ChevronsRight size={18} />}
                    </div>
                    {activeSection === 'resume' && (
                        <div className="training-accordion-content">
                            <fieldset className="control-fieldset">
                                <legend className="control-legend" style={{ color: '#D4AF37' }}>
                                    <RefreshCw size={16} /> Resume
                                </legend>
                                <div className="form-group">
                                    <label className="form-label">Checkpoint</label>
                                    <select
                                        name="selectedCheckpoint"
                                        value={resumeConfig.selectedCheckpoint}
                                        onChange={handleResumeChange}
                                        className="form-select"
                                        disabled={checkpointsLoading}
                                    >
                                        <option value="">Select a checkpoint...</option>
                                        {checkpointOptions.map((checkpoint) => (
                                            <option key={checkpoint} value={checkpoint}>
                                                {checkpoint}
                                            </option>
                                        ))}
                                    </select>
                                    {checkpointsError && (
                                        <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#b91c1c' }}>
                                            {checkpointsError}
                                        </div>
                                    )}
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Additional epochs</label>
                                    <input type="number" name="numAdditionalEpisodes" value={resumeConfig.numAdditionalEpisodes} onChange={handleResumeChange} className="form-input" min="1" />
                                </div>
                            </fieldset>

                            <div className="form-actions">
                                <button type="button" className="btn-primary btn-narrow" style={{ backgroundColor: '#D4AF37' }} disabled title="Use the checkpoint preview to resume training">
                                    <RefreshCw /> Use checkpoint preview to resume
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div >
    );
};
