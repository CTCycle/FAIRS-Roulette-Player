import React, { useState } from 'react';
import { Settings, Play, RefreshCw, Cpu, Layers, Database, Activity, HardDrive, Save, BarChart2 } from 'lucide-react';

interface TrainingControlsProps {
    onTrainingStart?: () => void;
}

export const TrainingControls: React.FC<TrainingControlsProps> = ({ onTrainingStart }) => {
    const [newConfig, setNewConfig] = useState({
        // Agent
        perceptiveField: 64,
        numNeurons: 64,
        embeddingDims: 200,
        explorationRate: 0.75,
        explorationRateDecay: 0.995,
        minExplorationRate: 0.10,
        discountRate: 0.50,
        modelUpdateFreq: 10,
        // Environment
        betAmount: 10,
        initialCapital: 1000,
        renderEnv: false,
        renderUpFreq: 50,
        // Dataset
        useDataGen: false,
        numGeneratedSamples: 10000,
        trainSampleSize: 1.0,
        validationSize: 0.20,
        splitSeed: 42,
        setShuffle: true,
        shuffleSize: 256,
        // Session - Training
        episodes: 10,
        maxStepsEpisode: 2000,
        batchSize: 32,
        learningRate: 0.0001,
        trainingSeed: 42,
        // Session - Device
        deviceGPU: false,
        deviceID: 0,
        // Memory
        maxMemorySize: 10000,
        replayBufferSize: 1000,
        // Checkpointing
        saveCheckpoints: false,
        checkpointsFreq: 1,
        useTensorboard: false
    });

    const [resumeConfig, setResumeConfig] = useState({
        numAdditionalEpisodes: 10
    });

    const handleNewChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value, type, checked } = e.target;
        setNewConfig(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleResumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setResumeConfig(prev => ({
            ...prev,
            [name]: value
        }));
    };

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
            render_environment: newConfig.renderEnv,
            render_update_frequency: Number(newConfig.renderUpFreq),
            // Dataset
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
            // Memory
            max_memory_size: Number(newConfig.maxMemorySize),
            replay_buffer_size: Number(newConfig.replayBufferSize),
            // Checkpointing
            save_checkpoints: newConfig.saveCheckpoints,
            checkpoints_frequency: Number(newConfig.checkpointsFreq),
            use_tensorboard: newConfig.useTensorboard,
        };

        try {
            const response = await fetch('/training/start', {
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
        try {
            const response = await fetch('/training/resume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    checkpoint: '', // TODO: Add checkpoint selector
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
        } catch (err) {
            console.error('Error resuming training:', err);
            alert('Failed to connect to training server');
        }
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
                <details className="training-accordion" open>
                    <summary className="training-accordion-summary">
                        <span className="training-accordion-title">
                            <Play size={18} /> New Training Session
                        </span>
                    </summary>
                    <div className="training-accordion-content">
                        <form onSubmit={handleNewSubmit}>
                            {/* AGENT GROUP */}
                            <fieldset className="control-fieldset">
                                <legend className="control-legend" style={{ color: '#E31D2B' }}>
                                    <Activity size={16} /> Agent
                                </legend>
                                <div className="param-grid">
                                    <div className="form-group">
                                        <label className="form-label">Perceptive Field Size</label>
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
                                        <label className="form-label">Weights Update Freq</label>
                                        <input type="number" name="modelUpdateFreq" value={newConfig.modelUpdateFreq} onChange={handleNewChange} className="form-input" max="1000" />
                                    </div>
                                </div>

                                <div className="param-grid">
                                    <div className="form-group">
                                        <label className="form-label">Exploration Rate</label>
                                        <input type="number" name="explorationRate" value={newConfig.explorationRate} onChange={handleNewChange} className="form-input" step="0.01" max="1.0" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Decay</label>
                                        <input type="number" name="explorationRateDecay" value={newConfig.explorationRateDecay} onChange={handleNewChange} className="form-input" step="0.001" max="1.0" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Min Rate</label>
                                        <input type="number" name="minExplorationRate" value={newConfig.minExplorationRate} onChange={handleNewChange} className="form-input" step="0.01" max="1.0" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Discount Rate</label>
                                        <input type="number" name="discountRate" value={newConfig.discountRate} onChange={handleNewChange} className="form-input" step="0.01" max="1.0" />
                                    </div>
                                </div>
                            </fieldset>

                            {/* ENVIRONMENT GROUP */}
                            <fieldset className="control-fieldset">
                                <legend className="control-legend" style={{ color: '#00933C' }}>
                                    <Layers size={16} /> Environment
                                </legend>
                                <div className="param-grid">
                                    <div className="form-group">
                                        <label className="form-label">Bet Amount</label>
                                        <input type="number" name="betAmount" value={newConfig.betAmount} onChange={handleNewChange} className="form-input" min="1" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Initial Capital</label>
                                        <input type="number" name="initialCapital" value={newConfig.initialCapital} onChange={handleNewChange} className="form-input" min="1" />
                                    </div>
                                </div>
                                <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                                    <input type="checkbox" id="renderEnv" name="renderEnv" checked={newConfig.renderEnv} onChange={handleNewChange} />
                                    <label htmlFor="renderEnv" className="form-label" style={{ marginBottom: 0 }}>Render environment every N steps</label>
                                    {newConfig.renderEnv && (
                                        <input type="number" name="renderUpFreq" value={newConfig.renderUpFreq} onChange={handleNewChange} className="form-input" style={{ width: '80px', marginLeft: 'auto' }} />
                                    )}
                                </div>
                            </fieldset>

                            {/* DATASET GROUP */}
                            <fieldset className="control-fieldset">
                                <legend className="control-legend" style={{ color: '#D4AF37' }}>
                                    <Database size={16} /> Training Data
                                </legend>

                                <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <input type="checkbox" id="useDataGen" name="useDataGen" checked={newConfig.useDataGen} onChange={handleNewChange} />
                                    <label htmlFor="useDataGen" className="form-label" style={{ marginBottom: 0 }}>Use data generator (N samples)</label>
                                    {newConfig.useDataGen && (
                                        <input type="number" name="numGeneratedSamples" value={newConfig.numGeneratedSamples} onChange={handleNewChange} className="form-input" style={{ width: '100px', marginLeft: 'auto' }} />
                                    )}
                                </div>

                                <div className="param-grid" style={{ marginTop: '0.5rem' }}>
                                    <div className="form-group">
                                        <label className="form-label">Train Sample Size</label>
                                        <input type="number" name="trainSampleSize" value={newConfig.trainSampleSize} onChange={handleNewChange} className="form-input" step="0.05" max="1.0" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Validation Size</label>
                                        <input type="number" name="validationSize" value={newConfig.validationSize} onChange={handleNewChange} className="form-input" step="0.05" max="1.0" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Split Seed</label>
                                        <input type="number" name="splitSeed" value={newConfig.splitSeed} onChange={handleNewChange} className="form-input" />
                                    </div>
                                </div>
                                <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                                    <input type="checkbox" id="setShuffle" name="setShuffle" checked={newConfig.setShuffle} onChange={handleNewChange} />
                                    <label htmlFor="setShuffle" className="form-label" style={{ marginBottom: 0 }}>Shuffle with buffer</label>
                                    {newConfig.setShuffle && (
                                        <input type="number" name="shuffleSize" value={newConfig.shuffleSize} onChange={handleNewChange} className="form-input" style={{ width: '80px', marginLeft: 'auto' }} />
                                    )}
                                </div>
                            </fieldset>

                            {/* SESSION GROUP */}
                            <fieldset className="control-fieldset">
                                <legend className="control-legend" style={{ color: '#94a3b8' }}>
                                    <Cpu size={16} /> Session
                                </legend>
                                <div className="param-grid">
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
                                </div>
                                <div className="param-grid">
                                    <div className="form-group">
                                        <label className="form-label">Training Seed</label>
                                        <input type="number" name="trainingSeed" value={newConfig.trainingSeed} onChange={handleNewChange} className="form-input" />
                                    </div>
                                </div>
                                <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                                    <input type="checkbox" id="deviceGPU" name="deviceGPU" checked={newConfig.deviceGPU} onChange={handleNewChange} />
                                    <label htmlFor="deviceGPU" className="form-label" style={{ marginBottom: 0 }}>Use GPU (Device ID)</label>
                                    {newConfig.deviceGPU && (
                                        <input type="number" name="deviceID" value={newConfig.deviceID} onChange={handleNewChange} className="form-input" style={{ width: '60px', marginLeft: 'auto' }} />
                                    )}
                                </div>
                            </fieldset>

                            {/* MEMORY GROUP */}
                            <fieldset className="control-fieldset">
                                <legend className="control-legend" style={{ color: '#7c3aed' }}>
                                    <HardDrive size={16} /> Memory
                                </legend>
                                <div className="param-grid">
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

                            {/* CHECKPOINTING GROUP */}
                            <fieldset className="control-fieldset">
                                <legend className="control-legend" style={{ color: '#06b6d4' }}>
                                    <Save size={16} /> Checkpointing
                                </legend>
                                <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <input type="checkbox" id="saveCheckpoints" name="saveCheckpoints" checked={newConfig.saveCheckpoints} onChange={handleNewChange} />
                                    <label htmlFor="saveCheckpoints" className="form-label" style={{ marginBottom: 0 }}>Save every N episodes</label>
                                    {newConfig.saveCheckpoints && (
                                        <input type="number" name="checkpointsFreq" value={newConfig.checkpointsFreq} onChange={handleNewChange} className="form-input" style={{ width: '60px', marginLeft: 'auto' }} min="1" />
                                    )}
                                </div>
                                <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                                    <input type="checkbox" id="useTensorboard" name="useTensorboard" checked={newConfig.useTensorboard} onChange={handleNewChange} />
                                    <label htmlFor="useTensorboard" className="form-label" style={{ marginBottom: 0 }}>
                                        <BarChart2 size={14} style={{ marginRight: '0.25rem' }} /> Enable TensorBoard
                                    </label>
                                </div>
                            </fieldset>

                            <button type="submit" className="btn-primary">
                                <Play /> Start Training
                            </button>
                        </form>
                    </div>
                </details>

                <details className="training-accordion">
                    <summary className="training-accordion-summary">
                        <span className="training-accordion-title">
                            <RefreshCw size={18} /> Resume Training Session
                        </span>
                    </summary>
                    <div className="training-accordion-content">
                        <fieldset className="control-fieldset">
                            <legend className="control-legend" style={{ color: '#D4AF37' }}>
                                <RefreshCw size={16} /> Resume
                            </legend>
                            <div className="form-group">
                                <label className="form-label">Additional epochs</label>
                                <input type="number" name="numAdditionalEpisodes" value={resumeConfig.numAdditionalEpisodes} onChange={handleResumeChange} className="form-input" min="1" />
                            </div>
                        </fieldset>

                        <button type="button" className="btn-primary" style={{ backgroundColor: '#D4AF37' }} onClick={handleResume}>
                            <RefreshCw /> Resume
                        </button>
                    </div>
                </details>
            </div>
        </div>
    );
};
