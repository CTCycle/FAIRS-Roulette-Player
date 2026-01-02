import React, { useEffect, useState } from 'react';
import { Settings, Play, RefreshCw, Cpu, Layers, Activity, Database, ChevronsDown, ChevronsRight } from 'lucide-react';
import type { TrainingNewConfig, TrainingResumeConfig } from '../../../context/AppStateContext';

interface TrainingControlsProps {
    newConfig: TrainingNewConfig;
    resumeConfig: TrainingResumeConfig;
    onNewConfigChange: (updates: Partial<TrainingNewConfig>) => void;
    onResumeConfigChange: (updates: Partial<TrainingResumeConfig>) => void;
    onTrainingStart?: () => void;
    datasetRefreshKey: number;
}

export const TrainingControls: React.FC<TrainingControlsProps> = ({
    newConfig,
    resumeConfig,
    onNewConfigChange,
    onResumeConfigChange,
    onTrainingStart,
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

    const handleNewSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        const config = {
            // Agent
            perceptive_field_size: Number(newConfig.perceptiveField),
            QNet_neurons: Number(newConfig.numNeurons),
            embedding_dimensions: Number(newConfig.embeddingDims),
            exploration_rate: Number(newConfig.explorationRate),
            exploration_rate_decay: Number(newConfig.explorationRateDecay),
            minimum_exploration_rate: Number(newConfig.minExplorationRate),
            discount_rate: Number(newConfig.discountRate),
            model_update_frequency: Number(newConfig.modelUpdateFreq),
            // Environment
            bet_amount: Number(newConfig.betAmount),
            initial_capital: Number(newConfig.initialCapital),
            // Dataset
            dataset_name: newConfig.datasetName,
            use_data_generator: newConfig.useDataGen,
            num_generated_samples: Number(newConfig.numGeneratedSamples),
            sample_size: Number(newConfig.trainSampleSize),
            validation_size: Number(newConfig.validationSize),
            seed: Number(newConfig.splitSeed),
            shuffle_dataset: newConfig.setShuffle,
            shuffle_size: Number(newConfig.shuffleSize),
            // Session
            episodes: Number(newConfig.episodes),
            max_steps_episode: Number(newConfig.maxStepsEpisode),
            batch_size: Number(newConfig.batchSize),
            learning_rate: Number(newConfig.learningRate),
            training_seed: Number(newConfig.trainingSeed),
            use_device_GPU: newConfig.deviceGPU,
            device_ID: Number(newConfig.deviceID),
            use_mixed_precision: newConfig.useMixedPrecision,
            num_workers: Number(newConfig.numWorkers),
            // Memory
            max_memory_size: Number(newConfig.maxMemorySize),
            replay_buffer_size: Number(newConfig.replayBufferSize),
            // Checkpointing
            save_checkpoints: newConfig.saveCheckpoints,
            checkpoints_frequency: Number(newConfig.checkpointsFreq),
            use_tensorboard: newConfig.useTensorboard,
        };

        try {
            const response = await fetch('/api/training/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config),
            });

            if (!response.ok) {
                const error = await response.json();
                console.error('Training start failed:', error);
                alert(`Failed to start training: ${error.detail || 'Unknown error'}`);
                return;
            }

            console.log('Training started successfully');
            onTrainingStart?.();
        } catch (err) {
            console.error('Error starting training:', err);
            alert('Failed to connect to training server');
        }
    };

    const handleResume = async () => {
        if (!resumeConfig.selectedCheckpoint) {
            alert('Please select a checkpoint to resume from.');
            return;
        }
        try {
            const response = await fetch('/api/training/resume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    checkpoint: resumeConfig.selectedCheckpoint,
                    additional_episodes: Number(resumeConfig.numAdditionalEpisodes),
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                console.error('Resume training failed:', error);
                alert(`Failed to resume training: ${error.detail || 'Unknown error'}`);
                return;
            }

            console.log('Resume training started successfully');
            onTrainingStart?.();
        } catch (err) {
            console.error('Error resuming training:', err);
            alert('Failed to connect to training server');
        }
    };

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
                            <form onSubmit={handleNewSubmit}>
                                {/* === AGENT CONFIGURATION === */}
                                <fieldset className="control-fieldset">
                                    <legend className="control-legend">
                                        <Activity size={16} className="text-blue-500" /> Agent Configuration
                                    </legend>
                                    <div className="training-pro-grid">
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

                                {/* === ENVIRONMENT & MEMORY === */}
                                <fieldset className="control-fieldset">
                                    <legend className="control-legend">
                                        <Layers size={16} /> Environment & Memory
                                    </legend>
                                    <div className="training-pro-grid">
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

                                {/* === DATASET === */}
                                <fieldset className="control-fieldset">
                                    <legend className="control-legend">
                                        <Database size={16} /> Dataset Configuration
                                    </legend>
                                    <div className="training-pro-grid">
                                        <div className="form-group" style={{ gridColumn: 'span 2' }}>
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
                                        <div className="form-group">
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


                                    {/* Dataset Toggles */}
                                    <div className="dataset-options-grid" style={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: '0.75rem',
                                        marginTop: '1rem',
                                        padding: '1rem',
                                        backgroundColor: 'rgba(255, 255, 255, 0.03)',
                                        borderRadius: '6px',
                                        border: '1px solid rgba(255, 255, 255, 0.05)'
                                    }}>
                                        {/* Data Generator Toggle */}
                                        <div className="dataset-option-group" style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                                            <label className="checkbox-visual" style={{ marginBottom: 0 }}>
                                                <input type="checkbox" name="useDataGen" checked={newConfig.useDataGen} onChange={handleNewChange} />
                                                <span style={{ fontWeight: 500 }}>Use synthetic data generator</span>
                                            </label>
                                            <div className="inline-input-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: newConfig.useDataGen ? 1 : 0.5 }}>
                                                <input type="number" name="numGeneratedSamples" value={newConfig.numGeneratedSamples} onChange={handleNewChange} className="form-input inline-input-sm" disabled={!newConfig.useDataGen} />
                                                <span style={{ fontSize: '0.85rem', color: '#64748b' }}>samples</span>
                                            </div>
                                        </div>

                                        {/* Shuffle Toggle */}
                                        <div className="dataset-option-group" style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                                            <label className="checkbox-visual" style={{ marginBottom: 0 }}>
                                                <input type="checkbox" name="setShuffle" checked={newConfig.setShuffle} onChange={handleNewChange} />
                                                <span style={{ fontWeight: 500 }}>Shuffle buffer</span>
                                            </label>
                                            <div className="inline-input-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: newConfig.setShuffle ? 1 : 0.5 }}>
                                                <input type="number" name="shuffleSize" value={newConfig.shuffleSize} onChange={handleNewChange} className="form-input inline-input-sm" disabled={!newConfig.setShuffle} />
                                                <span style={{ fontSize: '0.85rem', color: '#64748b' }}>size</span>
                                            </div>
                                        </div>
                                    </div>
                                </fieldset>


                                {/* === SESSION & COMPUTE === */}
                                <fieldset className="control-fieldset">
                                    <legend className="control-legend">
                                        <Cpu size={16} /> Session & Compute
                                    </legend>
                                    <div className="training-pro-grid">
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


                                    {/* Configuration Options */}
                                    <div className="session-options-container" style={{
                                        display: 'grid',
                                        gridTemplateColumns: '1fr 1fr',
                                        gap: '1.5rem',
                                        marginTop: '1.5rem'
                                    }}>
                                        {/* Hardware Acceleration Column */}
                                        <div className="session-option-column" style={{
                                            padding: '1rem',
                                            backgroundColor: 'rgba(255, 255, 255, 0.03)',
                                            borderRadius: '6px',
                                            border: '1px solid rgba(255, 255, 255, 0.05)'
                                        }}>
                                            <h4 style={{
                                                fontSize: '0.9rem',
                                                fontWeight: 600,
                                                color: '#94a3b8',
                                                marginBottom: '0.75rem',
                                                textTransform: 'uppercase',
                                                letterSpacing: '0.05em'
                                            }}>Hardware Acceleration</h4>

                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
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

                                        {/* Monitoring & Persistence Column */}
                                        <div className="session-option-column" style={{
                                            padding: '1rem',
                                            backgroundColor: 'rgba(255, 255, 255, 0.03)',
                                            borderRadius: '6px',
                                            border: '1px solid rgba(255, 255, 255, 0.05)'
                                        }}>
                                            <h4 style={{
                                                fontSize: '0.9rem',
                                                fontWeight: 600,
                                                color: '#94a3b8',
                                                marginBottom: '0.75rem',
                                                textTransform: 'uppercase',
                                                letterSpacing: '0.05em'
                                            }}>Monitoring & Persistence</h4>

                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                                <label className="checkbox-visual">
                                                    <input type="checkbox" name="useTensorboard" checked={newConfig.useTensorboard} onChange={handleNewChange} />
                                                    <span>Enable TensorBoard</span>
                                                </label>

                                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                                                    <label className="checkbox-visual" style={{ marginBottom: 0 }}>
                                                        <input type="checkbox" name="saveCheckpoints" checked={newConfig.saveCheckpoints} onChange={handleNewChange} />
                                                        <span>Save Checkpoints</span>
                                                    </label>
                                                    <div className="inline-input-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: newConfig.saveCheckpoints ? 1 : 0.5 }}>
                                                        <span style={{ fontSize: '0.85rem', color: '#64748b' }}>every</span>
                                                        <input type="number" name="checkpointsFreq" value={newConfig.checkpointsFreq} onChange={handleNewChange} className="form-input inline-input-sm" disabled={!newConfig.saveCheckpoints} />
                                                        <span style={{ fontSize: '0.85rem', color: '#64748b' }}>episodes</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </fieldset>

                                <div className="form-actions">
                                    <button type="submit" className="btn-primary btn-narrow">
                                        <Play size={18} /> Start Training Session
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
                                <button type="button" className="btn-primary btn-narrow" style={{ backgroundColor: '#D4AF37' }} onClick={handleResume} disabled={!resumeConfig.selectedCheckpoint}>
                                    <RefreshCw /> Resume
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div >
    );
};
