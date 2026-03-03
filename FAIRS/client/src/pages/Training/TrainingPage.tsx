import React, { useState } from 'react';
import { useAppState } from '../../context/AppStateContext';
import { useDatasetUploadState } from '../../hooks/useDatasetUploadState';
import './Training.css';
import { TrainingDashboard } from './components/TrainingDashboard';
import { DatasetUpload } from './components/DatasetUpload';
import { DatasetPreview } from './components/DatasetPreview';
import { CheckpointPreview } from './components/CheckpointPreview';

const TrainingPage: React.FC = () => {
    const { state, dispatch } = useAppState();
    const { isTraining } = state.training;
    const {
        datasetUpload,
        updateDatasetUploadState,
        resetDatasetUploadState,
    } = useDatasetUploadState();
    const [datasetRefreshKey, setDatasetRefreshKey] = useState(0);

    const handleUploadSuccess = () => {
        setDatasetRefreshKey((prev) => prev + 1);
    };

    const handleDatasetDelete = () => {
        setDatasetRefreshKey((prev) => prev + 1);
    };

    return (
        <div className="training-page">
            <div className="page-header">
                <h1 className="page-title">Training Dashboard</h1>
            </div>

            <div className="training-content">
                {/* Top Row: Upload (30%) + Dataset Preview (70%) */}
                <div className="training-top-row">
                    <div className="upload-column">
                        <DatasetUpload
                            uploadStatus={datasetUpload.uploadStatus}
                            uploadMessage={datasetUpload.uploadMessage}
                            onStateChange={updateDatasetUploadState}
                            onReset={resetDatasetUploadState}
                            onUploadSuccess={handleUploadSuccess}
                        />
                    </div>
                    <div className="preview-column">
                        <DatasetPreview
                            refreshKey={datasetRefreshKey}
                            onDelete={handleDatasetDelete}
                        />
                    </div>
                </div>

                <div className="section-separator" />

                {/* Second Row: Info (30%) + Checkpoints (70%) */}
                <div className="checkpoints-row">
                    <div className="info-column">
                        <div className="info-content">
                            <h3>Checkpoints</h3>
                            <p>
                                Your trained models are saved automatically as checkpoints (right). The system handles all data preprocessing, including normalization and validation splits, ensuring your models are ready for inference or continued training.
                            </p>
                        </div>
                    </div>
                    <div className="checkpoints-column">
                        <CheckpointPreview refreshKey={datasetRefreshKey} />
                    </div>
                </div>
            </div>

            <div className="section-separator training-dashboard-separator" />

            <TrainingDashboard
                isActive={isTraining}
                onTrainingStart={() => dispatch({ type: 'SET_TRAINING_IS_TRAINING', payload: true })}
                onTrainingEnd={() => dispatch({ type: 'SET_TRAINING_IS_TRAINING', payload: false })}
            />
        </div>
    );
};

export default TrainingPage;
