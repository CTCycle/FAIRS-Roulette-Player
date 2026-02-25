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

    const messageVariantClass = uploadStatus === 'success'
        ? 'upload-message-success'
        : uploadStatus === 'error'
            ? 'upload-message-error'
            : 'upload-message-info';


    return (
        <div className="dataset-section">
            <div className="dataset-upload-controls">
                <div
                    className={`upload-area ${selectedFile ? 'active' : ''}`}
                    role="button"
                    tabIndex={0}
                    onClick={() => fileInputRef.current?.click()}
                    onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            fileInputRef.current?.click();
                        }
                    }}
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
                    aria-label={selectedFile ? `Selected file ${selectedFile.name}` : 'Upload dataset file'}
                >
                    {selectedFile ? (
                        <>
                            <FileIcon className="upload-icon upload-icon-active" />
                            <div className="upload-text upload-text-active">
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
                        className="hidden-file-input"
                        accept=".csv,.xlsx,.xls"
                    />
                </div>

                <div className="upload-actions-row">
                    <button
                        type="button"
                        className="btn-primary upload-button-grow"
                        onClick={uploadDataset}
                        disabled={!selectedFile || uploadStatus === 'uploading'}
                    >
                        <Upload size={16} className="upload-button-icon" /> Upload Data
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
                        className={`upload-message ${messageVariantClass}`}
                        role="status"
                        aria-live="polite"
                    >
                        {uploadMessage}
                    </div>
                )}
            </div>
        </div>
    );
};
