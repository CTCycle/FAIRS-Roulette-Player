import React, { useRef, useState } from 'react';
import { Upload, Folder, File, X } from 'lucide-react';
import type { FileMetadata } from '../../../context/AppStateContext';

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
                            style={{ height: '100%', minHeight: '120px' }}
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
                                style={{ display: 'none' }}
                                accept=".csv,.xlsx,.xls"
                            />
                        </div>

                        {/* File Info + Clear Selection (Moved here to match width of dropzone) */}
                        <div className="dataset-v2-bottom" style={{ marginTop: '1rem' }}>
                            <div className="dataset-v2-file-info">
                                {files.length > 0 ? (
                                    <>
                                        <File className="file-icon" size={18} />
                                        <span className="file-name" title={files[0].name} style={{ fontWeight: 600 }}>
                                            {files[0].name}
                                        </span>
                                        <span className="file-size">{formatSize(files[0].size)}</span>
                                    </>
                                ) : (
                                    <span style={{ color: '#9CA3AF', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
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
                                style={{
                                    marginTop: 0,
                                    width: '100%',
                                    opacity: !selectedFile || uploadStatus === 'uploading' ? 0.7 : 1
                                }}
                            >
                                <Upload /> Upload
                            </button>

                            {uploadMessage && (
                                <div
                                    style={{
                                        marginTop: '0.5rem',
                                        padding: '0.5rem',
                                        borderRadius: '6px',
                                        fontSize: '0.75rem',
                                        lineHeight: '1.25',
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
                        </div>
                    </div>
                </div>
            </div>

            {/* Separator mostly hidden or removed spacing */}
            <div style={{ paddingBottom: '0.5rem' }}></div>

            {/* Configuration moved to TrainingControls */}
            <div style={{ paddingBottom: '1rem' }}></div>
        </div>
    );
};
