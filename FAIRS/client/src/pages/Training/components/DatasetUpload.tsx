import React from 'react';
import { Upload, File as FileIcon, X } from 'lucide-react';
import {
    formatFileSize,
    type DatasetUploadStatus,
} from '../../../utils/datasetUpload';
import type { DatasetUploadStateUpdates } from '../../../types/datasetUpload';
import { useDatasetFileUpload } from '../../../components/datasetUpload/useDatasetFileUpload';
import { UploadStatusMessage } from '../../../components/datasetUpload/UploadStatusMessage';
import { DatasetFileDropzone } from '../../../components/datasetUpload/DatasetFileDropzone';

interface DatasetUploadProps {
    uploadStatus: DatasetUploadStatus;
    uploadMessage: string;
    onStateChange: (updates: DatasetUploadStateUpdates) => void;
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
        onUploadSuccess,
    });

    return (
        <div className="dataset-section">
            <div className="dataset-upload-controls">
                <DatasetFileDropzone
                    className={`upload-area ${selectedFile ? 'active' : ''}`}
                    ariaLabel={selectedFile ? `Selected file ${selectedFile.name}` : 'Upload dataset file'}
                    fileInputRef={fileInputRef}
                    onFileChange={handleFileChange}
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
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
                </DatasetFileDropzone>

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
                <UploadStatusMessage uploadStatus={uploadStatus} uploadMessage={uploadMessage} />
            </div>
        </div>
    );
};
