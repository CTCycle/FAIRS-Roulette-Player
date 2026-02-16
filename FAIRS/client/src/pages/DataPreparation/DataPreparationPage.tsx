import React from 'react';
import { useAppState } from '../../context/AppStateContext';
import { DatasetUpload } from './components/DatasetUpload';
import './DataPreparation.css';

const DataPreparationPage: React.FC = () => {
    const { state, dispatch } = useAppState();
    // Reusing training state for now as agreed
    const { datasetUpload } = state.training;

    const handleDatasetUploadStateChange = (updates: {
        files?: typeof datasetUpload.files;
        uploadStatus?: typeof datasetUpload.uploadStatus;
        uploadMessage?: string;
    }) => {
        dispatch({ type: 'SET_DATASET_UPLOAD_STATE', payload: updates });
    };

    return (
        <div className="data-preparation-page">
            <div className="page-header">
                <h1 className="page-title">Dataset Preparation</h1>
                <p className="page-subtitle">Upload, validate, and prepare your data for training.</p>
            </div>

            <div className="preparation-content">
                <section className="upload-section">
                    <DatasetUpload
                        files={datasetUpload.files}
                        uploadStatus={datasetUpload.uploadStatus}
                        uploadMessage={datasetUpload.uploadMessage}
                        onStateChange={handleDatasetUploadStateChange}
                        onReset={() => dispatch({ type: 'RESET_DATASET_UPLOAD' })}
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
