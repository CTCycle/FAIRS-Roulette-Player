import React, { useState } from 'react';
import { useDatasetUploadState } from '../../hooks/useDatasetUploadState';
import { useTrainingStatus } from '../../hooks/useTrainingStatus';
import './Training.css';
import { TrainingDashboard } from './components/TrainingDashboard';
import { DatasetUpload } from './components/DatasetUpload';
import { DatasetPreview } from './components/DatasetPreview';
import { CheckpointPreview } from './components/CheckpointPreview';

const TrainingPage: React.FC = () => {
    const trainingStatus = useTrainingStatus();
    const { status, isConnected, connectionError, isStopping, stopError, stopTraining } = trainingStatus;
    const isTraining = status.is_training;
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
                <p className="page-subtitle">
                    Upload roulette datasets, manage checkpoints, and monitor live agent training from a single surface.
                </p>
            </div>

            <div className="training-content">
                <div className="training-top-row">
                    <div className="upload-column" data-guidance-target="training-data">
                        <DatasetUpload
                            uploadStatus={datasetUpload.uploadStatus}
                            uploadMessage={datasetUpload.uploadMessage}
                            onStateChange={updateDatasetUploadState}
                            onReset={resetDatasetUploadState}
                            onUploadSuccess={handleUploadSuccess}
                        />
                    </div>
                    <div className="preview-column" data-guidance-target="training-configuration">
                        <DatasetPreview
                            refreshKey={datasetRefreshKey}
                            isTraining={isTraining}
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
                                Review trained model snapshots, compare checkpoint metadata, resume interrupted training runs, and launch evaluation sessions directly from the checkpoint panel.
                            </p>
                        </div>
                    </div>
                    <div className="checkpoints-column">
                        <CheckpointPreview refreshKey={datasetRefreshKey} isTraining={isTraining} />
                    </div>
                </div>
            </div>

            <div className="section-separator training-dashboard-separator" />

            <div data-guidance-target="training-monitor">
                <TrainingDashboard
                    status={status}
                    isConnected={isConnected}
                    connectionError={connectionError}
                    isStopping={isStopping}
                    stopError={stopError}
                    onStopTraining={stopTraining}
                />
            </div>
        </div>
    );
};

export default TrainingPage;

