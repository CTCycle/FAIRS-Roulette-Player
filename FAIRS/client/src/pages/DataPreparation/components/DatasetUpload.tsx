import React from 'react';
import { Upload, Folder, File, X } from 'lucide-react';
import type { FileMetadata } from '../../../context/AppStateContext';
import {
    formatFileSize,
    type DatasetUploadStatus,
} from '../../../utils/datasetUpload';
import type { DatasetUploadStateUpdates } from '../../../types/datasetUpload';
import { useDatasetFileUpload } from '../../../components/datasetUpload/useDatasetFileUpload';
import { UploadStatusMessage } from '../../../components/datasetUpload/UploadStatusMessage';
import { DatasetFileDropzone } from '../../../components/datasetUpload/DatasetFileDropzone';

interface DatasetUploadProps {
    files: FileMetadata[];
    uploadStatus: DatasetUploadStatus;
    uploadMessage: string;
    onStateChange: (updates: DatasetUploadStateUpdates) => void;
    onReset: () => void;
}

export const DatasetUpload: React.FC<DatasetUploadProps> = ({
    files,
    uploadStatus,
    uploadMessage,
    onStateChange,
    onReset,
}) => {
    const {
        selectedFile,
        fileInputRef,
        handleFileChange,
        handleDragOver,
        handleDrop,
        clearFiles,
        uploadDataset,
    } = useDatasetFileUpload({
        onStateChange,
        onReset,
    });

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
                        <DatasetFileDropzone
                            className="upload-area"
                            ariaLabel={selectedFile ? `Selected file ${selectedFile.name}` : 'Upload dataset file'}
                            fileInputRef={fileInputRef}
                            onFileChange={handleFileChange}
                            onDragOver={handleDragOver}
                            onDrop={handleDrop}
                        >
                            <Upload className="upload-icon" />
                            <div className="upload-text">
                                <strong>Click to upload</strong> or drag and drop
                            </div>
                            <div className="upload-hint">
                                Supports CSV/XLSX
                            </div>
                        </DatasetFileDropzone>

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
                                    type="button"
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

                            <UploadStatusMessage uploadStatus={uploadStatus} uploadMessage={uploadMessage} />
                        </div>
                    </div>
                </div>
            </div>

            <div className="dataset-v2-spacer-sm" />
            <div className="dataset-v2-spacer-md" />
        </div>
    );
};
