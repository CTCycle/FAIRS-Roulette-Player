import React from 'react';
import { DatasetUpload } from './components/DatasetUpload';
import { useDatasetUploadState } from '../../hooks/useDatasetUploadState';
import './DataPreparation.css';

const DataPreparationPage: React.FC = () => {
    const {
        datasetUpload,
        updateDatasetUploadState,
        resetDatasetUploadState,
    } = useDatasetUploadState();

    return (
        <div className="data-preparation-page page-shell">
            <div className="page-header">
                <p className="page-eyebrow">Datasets</p>
                <h1 className="page-title">Dataset Preparation</h1>
                <p className="page-subtitle">Upload, validate, and prepare your data for training.</p>
            </div>

            <div className="preparation-content">
                <section className="upload-section">
                    <DatasetUpload
                        files={datasetUpload.files}
                        uploadStatus={datasetUpload.uploadStatus}
                        uploadMessage={datasetUpload.uploadMessage}
                        onStateChange={updateDatasetUploadState}
                        onReset={resetDatasetUploadState}
                    />
                </section>

                <section className="validation-section">
                    <div className="card">
                        <div className="card-header">
                            <h2 className="card-title">Validation Tools</h2>
                        </div>
                        <div className="card-body">
                            <p className="text-muted">Data quality inspection and schema validation tools will appear here. For now, verify uploaded datasets from the Training workflow.</p>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
};

export default DataPreparationPage;
