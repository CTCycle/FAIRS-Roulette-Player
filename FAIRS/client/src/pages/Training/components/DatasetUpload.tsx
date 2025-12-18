import React, { useRef, useState } from 'react';
import { Upload, Folder, File, X, Database } from 'lucide-react';
import type { FileMetadata, TrainingNewConfig } from '../../../context/AppStateContext';

interface DatasetUploadProps {
    files: FileMetadata[];
    uploadStatus: 'idle' | 'uploading' | 'success' | 'error';
    uploadMessage: string;
    onStateChange: (updates: {
        files?: FileMetadata[];
        uploadStatus?: 'idle' | 'uploading' | 'success' | 'error';
        uploadMessage?: string;
    }) => void;
    onReset: () => void;
    // New props for generator config
    newConfig: TrainingNewConfig;
    onNewConfigChange: (updates: Partial<TrainingNewConfig>) => void;
}

export const DatasetUpload: React.FC<DatasetUploadProps> = ({
    files,
    uploadStatus,
    uploadMessage,
    onStateChange,
    onReset,
    newConfig,
    onNewConfigChange,
}) => {
    // Keep actual File object in local ref (not serializable for context)
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const formatSize = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const isSupportedFile = (file: File) => {
        const extension = file.name.split('.').pop()?.toLowerCase();
        return extension === 'csv' || extension === 'xlsx' || extension === 'xls';
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const file = e.target.files[0] ?? null;
            if (!file) return;
            if (!isSupportedFile(file)) {
                onStateChange({
                    uploadStatus: 'error',
                    uploadMessage: 'Unsupported file. Please upload a CSV or XLSX.',
                });
                return;
            }
            setSelectedFile(file);
            onStateChange({
                uploadStatus: 'idle',
                uploadMessage: '',
                files: [{ name: file.name, size: file.size, type: file.type }],
            });
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        const file = e.dataTransfer.files?.[0] ?? null;
        if (!file) return;
        if (!isSupportedFile(file)) {
            onStateChange({
                uploadStatus: 'error',
                uploadMessage: 'Unsupported file. Please upload a CSV or XLSX.',
            });
            return;
        }
        setSelectedFile(file);
        onStateChange({
            uploadStatus: 'idle',
            uploadMessage: '',
            files: [{ name: file.name, size: file.size, type: file.type }],
        });
    };

    const clearFiles = () => {
        setSelectedFile(null);
        onReset();
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const uploadDataset = async () => {
        if (!selectedFile) {
            onStateChange({
                uploadStatus: 'error',
                uploadMessage: 'Select a CSV/XLSX file first.',
            });
            return;
        }

        const endpoint = '/api/data/upload?table=ROULETTE_SERIES';

        onStateChange({
            uploadStatus: 'uploading',
            uploadMessage: 'Uploading and importing dataset...',
        });

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorPayload = (await response.json().catch(() => null)) as { detail?: string } | null;
                const detail = errorPayload?.detail ?? `Upload failed (HTTP ${response.status}).`;
                throw new Error(detail);
            }

            const payload = (await response.json().catch(() => null)) as { rows_imported?: number } | null;
            const rows = payload?.rows_imported ?? 0;
            onStateChange({
                uploadStatus: 'success',
                uploadMessage: `Imported ${rows} rows into the database.`,
            });
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Upload failed.';
            onStateChange({
                uploadStatus: 'error',
                uploadMessage: message,
            });
        }
    };

    const handleConfigChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value, type, checked } = e.target;
        onNewConfigChange({
            [name]: type === 'checkbox' ? checked : value
        } as Partial<TrainingNewConfig>);
    };

    return (
        <div className="card dataset-section">
            <div className="card-header">
                <h2 className="card-title">
                    <Folder size={24} />
                    Dataset Selection
                </h2>
            </div>

            <div
                className="upload-area"
                onClick={() => fileInputRef.current?.click()}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
            >
                <Upload className="upload-icon" />
                <div className="upload-text">
                    <strong>Click to upload</strong> or drag and drop
                </div>
                <div className="upload-hint">
                    Supports CSV/XLSX datasets
                </div>
                <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                    accept=".csv,.xlsx,.xls"
                />
            </div>

            <button
                type="button"
                className="btn-primary"
                onClick={uploadDataset}
                disabled={!selectedFile || uploadStatus === 'uploading'}
                style={{ opacity: !selectedFile || uploadStatus === 'uploading' ? 0.7 : 1 }}
            >
                <Upload /> Upload Data
            </button>

            {uploadMessage && (
                <div
                    style={{
                        marginTop: '0.75rem',
                        padding: '0.75rem',
                        borderRadius: '6px',
                        background:
                            uploadStatus === 'success'
                                ? '#ECFDF5'
                                : uploadStatus === 'error'
                                    ? '#FEF2F2'
                                    : '#EFF6FF',
                        color:
                            uploadStatus === 'success'
                                ? '#065F46'
                                : uploadStatus === 'error'
                                    ? '#991B1B'
                                    : '#1E40AF',
                        border:
                            uploadStatus === 'success'
                                ? '1px solid #A7F3D0'
                                : uploadStatus === 'error'
                                    ? '1px solid #FECACA'
                                    : '1px solid #BFDBFE',
                    }}
                >
                    {uploadMessage}
                </div>
            )}

            <div className="file-list">
                {files.length > 0 ? (
                    files.map((file, index) => (
                        <div key={index} className="file-item">
                            <File className="file-icon" />
                            <span className="file-name" title={file.name}>{file.name}</span>
                            <span className="file-size">{formatSize(file.size)}</span>
                        </div>
                    ))
                ) : (
                    <div style={{ textAlign: 'center', color: '#9CA3AF', marginTop: '2rem' }}>
                        No files selected
                    </div>
                )}
            </div>

            {files.length > 0 && (
                <button
                    onClick={(e) => { e.stopPropagation(); clearFiles(); }}
                    style={{
                        marginTop: '1rem',
                        background: 'transparent',
                        border: '1px solid #ddd',
                        padding: '0.5rem',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem',
                        color: '#666'
                    }}
                >
                    <X size={16} /> Clear Selection
                </button>
            )}

            <hr style={{ margin: '1.5rem 0', borderColor: '#e2e8f0' }} />

            {/* DATASET CONFIG GROUP */}
            <fieldset className="control-fieldset">
                <legend className="control-legend" style={{ color: '#D4AF37' }}>
                    <Database size={16} /> Training Data
                </legend>

                <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input type="checkbox" id="useDataGen" name="useDataGen" checked={newConfig.useDataGen} onChange={handleConfigChange} />
                    <label htmlFor="useDataGen" className="form-label" style={{ marginBottom: 0 }}>Use data generator (N samples)</label>
                    {newConfig.useDataGen && (
                        <input type="number" name="numGeneratedSamples" value={newConfig.numGeneratedSamples} onChange={handleConfigChange} className="form-input" style={{ width: '100px', marginLeft: 'auto' }} />
                    )}
                </div>

                <div className="param-grid" style={{ marginTop: '0.5rem', gridTemplateColumns: '1fr 1fr' }}>
                    <div className="form-group">
                        <label className="form-label">Train Sample Size</label>
                        <input type="number" name="trainSampleSize" value={newConfig.trainSampleSize} onChange={handleConfigChange} className="form-input" step="0.05" max="1.0" />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Validation Size</label>
                        <input type="number" name="validationSize" value={newConfig.validationSize} onChange={handleConfigChange} className="form-input" step="0.05" max="1.0" />
                    </div>
                </div>
                <div className="form-group" style={{ marginTop: '0.5rem' }}>
                    <label className="form-label">Split Seed</label>
                    <input type="number" name="splitSeed" value={newConfig.splitSeed} onChange={handleConfigChange} className="form-input" />
                </div>

                <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                    <input type="checkbox" id="setShuffle" name="setShuffle" checked={newConfig.setShuffle} onChange={handleConfigChange} />
                    <label htmlFor="setShuffle" className="form-label" style={{ marginBottom: 0 }}>Shuffle with buffer</label>
                    {newConfig.setShuffle && (
                        <input type="number" name="shuffleSize" value={newConfig.shuffleSize} onChange={handleConfigChange} className="form-input" style={{ width: '80px', marginLeft: 'auto' }} />
                    )}
                </div>
            </fieldset>
        </div>
    );
};
