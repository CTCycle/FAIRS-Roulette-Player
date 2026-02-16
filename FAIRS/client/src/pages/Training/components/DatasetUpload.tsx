import React, { useRef, useState } from 'react';
import { Upload, File as FileIcon, X } from 'lucide-react';
import type { FileMetadata } from '../../../context/AppStateContext';
import {
    formatFileSize,
    isSupportedDatasetFile,
    type DatasetUploadStatus,
    uploadDatasetFile,
} from '../../../utils/datasetUpload';

interface DatasetUploadProps {
    uploadStatus: DatasetUploadStatus;
    uploadMessage: string;
    onStateChange: (updates: {
        files?: FileMetadata[];
        uploadStatus?: DatasetUploadStatus;
        uploadMessage?: string;
    }) => void;
    onReset: () => void;
    onUploadSuccess?: () => void;
}

export const DatasetUpload: React.FC<DatasetUploadProps> = ({
    uploadStatus,
    uploadMessage,
    onStateChange,
    onReset,
    onUploadSuccess,
}) => {
    // Keep actual File object in local ref (not serializable for context)
    const [selectedFile, setSelectedFile] = useState<globalThis.File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const file = e.target.files[0] ?? null;
            if (!file) return;
            if (!isSupportedDatasetFile(file)) {
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
        if (!isSupportedDatasetFile(file)) {
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

        onStateChange({
            uploadStatus: 'uploading',
            uploadMessage: 'Uploading and importing dataset...',
        });

        try {
            const rows = await uploadDatasetFile(selectedFile);
            onStateChange({
                uploadStatus: 'success',
                uploadMessage: `Imported ${rows} rows into the database.`,
            });
            onUploadSuccess?.();
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Upload failed.';
            onStateChange({
                uploadStatus: 'error',
                uploadMessage: message,
            });
        }
    };



    return (
        <div className="dataset-section">
            <div className="dataset-upload-controls">
                <div
                    className={`upload-area ${selectedFile ? 'active' : ''}`}
                    onClick={() => fileInputRef.current?.click()}
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
                >
                    {selectedFile ? (
                        <>
                            <FileIcon className="upload-icon" style={{ color: 'var(--roulette-green)' }} />
                            <div className="upload-text" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                {selectedFile.name}
                            </div>
                            <div className="upload-hint">
                                {formatFileSize(selectedFile.size)}
                            </div>
                        </>
                    ) : (
                        <>
                            <Upload className="upload-icon" />
                            <div className="upload-text">
                                <strong>Click to upload</strong> or drag and drop
                            </div>
                            <div className="upload-hint">
                                Supports CSV/XLSX
                            </div>
                        </>
                    )}
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        style={{ display: 'none' }}
                        accept=".csv,.xlsx,.xls"
                    />
                </div>

                <div className="upload-actions-row">
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={uploadDataset}
                        disabled={!selectedFile || uploadStatus === 'uploading'}
                        style={{ flex: 1, padding: '0.5rem 1rem', opacity: !selectedFile || uploadStatus === 'uploading' ? 0.7 : 1 }}
                    >
                        <Upload size={16} style={{ marginRight: '0.5rem' }} /> Upload Data
                    </button>

                    {selectedFile && (
                        <button
                            type="button"
                            className="btn-clear"
                            onClick={(e) => { e.stopPropagation(); clearFiles(); }}
                        >
                            <X size={16} /> Clear
                        </button>
                    )}
                </div>

                {uploadMessage && (
                    <div
                        style={{
                            marginTop: '0.75rem',
                            padding: '0.5rem',
                            borderRadius: '6px',
                            fontSize: '0.85rem',
                            background:
                                uploadStatus === 'success'
                                    ? 'rgba(34, 197, 94, 0.16)'
                                    : uploadStatus === 'error'
                                        ? 'rgba(239, 68, 68, 0.16)'
                                        : 'rgba(56, 189, 248, 0.16)',
                            color:
                                uploadStatus === 'success'
                                    ? '#86efac'
                                    : uploadStatus === 'error'
                                        ? '#fecaca'
                                        : '#bae6fd',
                            border:
                                uploadStatus === 'success'
                                    ? '1px solid rgba(34, 197, 94, 0.45)'
                                    : uploadStatus === 'error'
                                        ? '1px solid rgba(239, 68, 68, 0.45)'
                                        : '1px solid rgba(56, 189, 248, 0.45)',
                        }}
                    >
                        {uploadMessage}
                    </div>
                )}
            </div>
        </div>
    );
};
