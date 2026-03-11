import React, { useState } from 'react';
import { useAppState } from '../../hooks/useAppState';
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
        <div className="training-page page-shell">
            <div className="page-header">
                <h1 className="page-title">Model Training Workspace</h1>
                <p className="page-subtitle">
                    Upload roulette datasets, manage checkpoints, and monitor live agent training from a single surface.
                </p>
            </div>

            <div className="training-content">
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

                <div className="checkpoints-row">
                    <div className="info-column">
                        <div className="info-content">
                            <h3>Checkpoints</h3>
                            <p>
                                Review trained snapshots, resume runs, or launch evaluation sessions directly from the checkpoint panel.
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

