import React, { useRef, useState } from 'react';
import { Upload, Folder, File, X } from 'lucide-react';
import type { FileMetadata } from '../../../context/AppStateContext';
import {
    formatFileSize,
    isSupportedDatasetFile,
    type DatasetUploadStatus,
    uploadDatasetFile,
} from '../../../utils/datasetUpload';

interface DatasetUploadProps {
    files: FileMetadata[];
    uploadStatus: DatasetUploadStatus;
    uploadMessage: string;
    onStateChange: (updates: {
        files?: FileMetadata[];
        uploadStatus?: DatasetUploadStatus;
        uploadMessage?: string;
    }) => void;
    onReset: () => void;
}

export const DatasetUpload: React.FC<DatasetUploadProps> = ({
    files,
    uploadStatus,
    uploadMessage,
    onStateChange,
    onReset,
}) => {
    // Keep actual File object in local ref (not serializable for context)
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
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
        <div className="card dataset-section">
            <div className="card-header">
                <h2 className="card-title">
                    <Folder size={24} />
                    Dataset Selection
                </h2>
            </div>

            {/* Horizontal Layout Container V2 */}
            <div className="dataset-v2-container">
                {/* Top Row: Dropzone (Left) + Upload Button (Right) */}
                <div className="dataset-v2-top">
                    <div className="dataset-v2-dropzone-wrapper">
                        <div
                            className="upload-area"
                            onClick={() => fileInputRef.current?.click()}
                            onDragOver={handleDragOver}
                            onDrop={handleDrop}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(event) => {
                                if (event.key === 'Enter' || event.key === ' ') {
                                    event.preventDefault();
                                    fileInputRef.current?.click();
                                }
                            }}
                            aria-label={selectedFile ? `Selected file ${selectedFile.name}` : 'Upload dataset file'}
                        >
                            <Upload className="upload-icon" />
                            <div className="upload-text">
                                <strong>Click to upload</strong> or drag and drop
                            </div>
                            <div className="upload-hint">
                                Supports CSV/XLSX
                            </div>
                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileChange}
                                className="hidden-file-input"
                                accept=".csv,.xlsx,.xls"
                            />
                        </div>

                        {/* File Info + Clear Selection (Moved here to match width of dropzone) */}
                        <div className="dataset-v2-bottom dataset-v2-bottom-spaced">
                            <div className="dataset-v2-file-info">
                                {files.length > 0 ? (
                                    <>
                                        <File className="file-icon" size={18} />
                                        <span className="file-name dataset-file-name-strong" title={files[0].name}>
                                            {files[0].name}
                                        </span>
                                        <span className="file-size">{formatFileSize(files[0].size)}</span>
                                    </>
                                ) : (
                                    <span className="dataset-file-placeholder">
                                        <File size={18} /> No dataset selected
                                    </span>
                                )}
                            </div>

                            {files.length > 0 && (
                                <button
                                    className="dataset-v2-clear-btn"
                                    onClick={(e) => { e.stopPropagation(); clearFiles(); }}
                                >
                                    <X size={16} /> Clear Selection
                                </button>
                            )}
                        </div>
                    </div>

                    <div className="dataset-v2-actions">
                        <div className="dataset-instruction-text">
                            Upload a series of roulette extractions in CSV or XLSX format.<br /><br />
                            The file must contain a <strong>single column</strong> with roulette numbers (0-36). Column name does not matter.
                        </div>

                        <div className="dataset-action-button-wrapper">
                            <button
                                type="button"
                                className="btn-primary"
                                onClick={uploadDataset}
                                disabled={!selectedFile || uploadStatus === 'uploading'}
                            >
                                <Upload /> Upload
                            </button>

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
                </div>
            </div>

            <div className="dataset-v2-spacer-sm" />
            <div className="dataset-v2-spacer-md" />
        </div>
    );
};
