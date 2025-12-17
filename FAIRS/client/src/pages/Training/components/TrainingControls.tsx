import React, { useState } from 'react';
import { Settings, Play, RefreshCw, Cpu, Layers, Database, Activity } from 'lucide-react';

export const TrainingControls: React.FC = () => {
  const [config, setConfig] = useState({
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
    renderUpFreq: 0,
    // Dataset (Training Specific)
    useDataGen: false,
    numGeneratedSamples: 10000,
    trainSampleSize: 1.0,
    validationSize: 0.20,
    splitSeed: 42,
    setShuffle: true,
    shuffleSize: 256,
    // Session
    deviceGPU: false,
    deviceID: 0,
    numWorkers: 0,
    numAdditionalEpisodes: 10
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setConfig(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Starting training with config:', config);
  };

  return (
    <div className="card controls-section">
      <div className="card-header">
        <h2 className="card-title">
          <Settings size={24} />
          Training Configuration
        </h2>
      </div>

      <form onSubmit={handleSubmit} style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 200px)', paddingRight: '0.5rem' }}>
        
        {/* AGENT GROUP */}
        <fieldset style={{ border: '1px solid #eee', borderRadius: '8px', padding: '1rem', marginBottom: '1.5rem' }}>
            <legend style={{ fontWeight: 600, color: '#E31D2B', padding: '0 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Activity size={16} /> Agent
            </legend>
            <div className="param-grid">
                <div className="form-group">
                    <label className="form-label">Perceptive Field Size</label>
                    <input type="number" name="perceptiveField" value={config.perceptiveField} onChange={handleChange} className="form-input" max="1024" />
                </div>
                <div className="form-group">
                    <label className="form-label">QNet Neurons</label>
                    <input type="number" name="numNeurons" value={config.numNeurons} onChange={handleChange} className="form-input" max="10000" />
                </div>
                <div className="form-group">
                    <label className="form-label">Embedding Dims</label>
                    <input type="number" name="embeddingDims" value={config.embeddingDims} onChange={handleChange} className="form-input" step="8" max="9999" />
                </div>
                <div className="form-group">
                    <label className="form-label">Weights Update Freq</label>
                    <input type="number" name="modelUpdateFreq" value={config.modelUpdateFreq} onChange={handleChange} className="form-input" max="1000" />
                </div>
            </div>
            
            <div className="param-grid">
                 <div className="form-group">
                    <label className="form-label">Exploration Rate</label>
                    <input type="number" name="explorationRate" value={config.explorationRate} onChange={handleChange} className="form-input" step="0.01" max="1.0" />
                </div>
                <div className="form-group">
                    <label className="form-label">Decay</label>
                    <input type="number" name="explorationRateDecay" value={config.explorationRateDecay} onChange={handleChange} className="form-input" step="0.001" max="1.0" />
                </div>
                <div className="form-group">
                    <label className="form-label">Min Rate</label>
                    <input type="number" name="minExplorationRate" value={config.minExplorationRate} onChange={handleChange} className="form-input" step="0.01" max="1.0" />
                </div>
                <div className="form-group">
                    <label className="form-label">Discount Rate</label>
                    <input type="number" name="discountRate" value={config.discountRate} onChange={handleChange} className="form-input" step="0.01" max="1.0" />
                </div>
            </div>
        </fieldset>

        {/* ENVIRONMENT GROUP */}
        <fieldset style={{ border: '1px solid #eee', borderRadius: '8px', padding: '1rem', marginBottom: '1.5rem' }}>
            <legend style={{ fontWeight: 600, color: '#00933C', padding: '0 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Layers size={16} /> Environment
            </legend>
             <div className="param-grid">
                <div className="form-group">
                    <label className="form-label">Bet Amount</label>
                    <input type="number" name="betAmount" value={config.betAmount} onChange={handleChange} className="form-input" min="1" />
                </div>
                <div className="form-group">
                    <label className="form-label">Initial Capital</label>
                    <input type="number" name="initialCapital" value={config.initialCapital} onChange={handleChange} className="form-input" min="1" />
                </div>
            </div>
             <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                <input type="checkbox" id="renderEnv" name="renderEnv" checked={config.renderEnv} onChange={handleChange} />
                <label htmlFor="renderEnv" className="form-label" style={{ marginBottom: 0 }}>Render environment every N steps</label>
                {config.renderEnv && (
                     <input type="number" name="renderUpFreq" value={config.renderUpFreq} onChange={handleChange} className="form-input" style={{ width: '80px', marginLeft: 'auto' }} />
                )}
            </div>
        </fieldset>

        {/* DATASET GROUP (Model Tab Variant) */}
        <fieldset style={{ border: '1px solid #eee', borderRadius: '8px', padding: '1rem', marginBottom: '1.5rem' }}>
            <legend style={{ fontWeight: 600, color: '#D4AF37', padding: '0 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Database size={16} /> Training Data
            </legend>
            
             <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input type="checkbox" id="useDataGen" name="useDataGen" checked={config.useDataGen} onChange={handleChange} />
                <label htmlFor="useDataGen" className="form-label" style={{ marginBottom: 0 }}>Use data generator (N samples)</label>
                 {config.useDataGen && (
                     <input type="number" name="numGeneratedSamples" value={config.numGeneratedSamples} onChange={handleChange} className="form-input" style={{ width: '100px', marginLeft: 'auto' }} />
                )}
            </div>

            <div className="param-grid" style={{ marginTop: '0.5rem' }}>
                <div className="form-group">
                    <label className="form-label">Train Sample Size</label>
                    <input type="number" name="trainSampleSize" value={config.trainSampleSize} onChange={handleChange} className="form-input" step="0.05" max="1.0" />
                </div>
                 <div className="form-group">
                    <label className="form-label">Validation Size</label>
                    <input type="number" name="validationSize" value={config.validationSize} onChange={handleChange} className="form-input" step="0.05" max="1.0" />
                </div>
                 <div className="form-group">
                    <label className="form-label">Split Seed</label>
                    <input type="number" name="splitSeed" value={config.splitSeed} onChange={handleChange} className="form-input" />
                </div>
            </div>
             <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                <input type="checkbox" id="setShuffle" name="setShuffle" checked={config.setShuffle} onChange={handleChange} />
                <label htmlFor="setShuffle" className="form-label" style={{ marginBottom: 0 }}>Shuffle with buffer</label>
                 {config.setShuffle && (
                     <input type="number" name="shuffleSize" value={config.shuffleSize} onChange={handleChange} className="form-input" style={{ width: '80px', marginLeft: 'auto' }} />
                )}
            </div>
        </fieldset>

         {/* SESSION GROUP */}
        <fieldset style={{ border: '1px solid #eee', borderRadius: '8px', padding: '1rem', marginBottom: '1.5rem' }}>
            <legend style={{ fontWeight: 600, color: '#333', padding: '0 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Cpu size={16} /> Session
            </legend>
            <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input type="checkbox" id="deviceGPU" name="deviceGPU" checked={config.deviceGPU} onChange={handleChange} />
                <label htmlFor="deviceGPU" className="form-label" style={{ marginBottom: 0 }}>Use GPU (Device ID)</label>
                 {config.deviceGPU && (
                     <input type="number" name="deviceID" value={config.deviceID} onChange={handleChange} className="form-input" style={{ width: '80px', marginLeft: 'auto' }} />
                )}
            </div>
            
             <div className="param-grid">
                <div className="form-group">
                    <label className="form-label">Workers</label>
                    <input type="number" name="numWorkers" value={config.numWorkers} onChange={handleChange} className="form-input" />
                </div>
                <div className="form-group">
                    <label className="form-label">Add. Episodes</label>
                    <input type="number" name="numAdditionalEpisodes" value={config.numAdditionalEpisodes} onChange={handleChange} className="form-input" />
                </div>
            </div>
        </fieldset>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <button type="submit" className="btn-primary">
            <Play /> Start Training
            </button>
            <button type="button" className="btn-primary" style={{ backgroundColor: '#D4AF37' }}>
            <RefreshCw /> Resume
            </button>
        </div>
      </form>
    </div>
  );
};
