import React, { useState } from 'react';
import { useDatasetUploadState } from '../../hooks/useDatasetUploadState';
import { useTrainingStatus } from '../../hooks/useTrainingStatus';
import { GuidanceDialog } from '../../components/guidance/GuidanceDialog';
import './Training.css';
import { TrainingDashboard } from './components/TrainingDashboard';
import { DatasetUpload } from './components/DatasetUpload';
import { DatasetPreview } from './components/DatasetPreview';
import { CheckpointPreview } from './components/CheckpointPreview';
import { CheckpointComparison } from './components/CheckpointComparison';

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
    const [checkpointRefreshKey, setCheckpointRefreshKey] = useState(0);
    const [comparisonOpen, setComparisonOpen] = useState(false);

    const handleUploadSuccess = () => {
        setDatasetRefreshKey((prev) => prev + 1);
    };

    const handleDatasetDelete = () => {
        setDatasetRefreshKey((prev) => prev + 1);
    };

    const handleCheckpointChange = () => {
        setCheckpointRefreshKey((prev) => prev + 1);
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
                                Review trained model snapshots, compare stored training summaries, resume interrupted runs, and open checkpoints in Inference while preserving dataset provenance.
                            </p>
                        </div>
                    </div>
                    <div className="checkpoints-column">
                        <CheckpointPreview
                            refreshKey={datasetRefreshKey}
                            isTraining={isTraining}
                            onChange={handleCheckpointChange}
                            onCompare={() => setComparisonOpen(true)}
                        />
                    </div>
                </div>
            </div>

            {comparisonOpen && (
                <GuidanceDialog
                    title="Compare Checkpoints"
                    description="Compare configuration and stored training summaries. These values are not a standardized benchmark."
                    labelledBy="checkpoint-comparison-dialog-title"
                    onClose={() => setComparisonOpen(false)}
                    className="guidance-checkpoint-comparison-dialog"
                >
                    <CheckpointComparison
                        refreshKey={checkpointRefreshKey}
                        labelledBy="checkpoint-comparison-dialog-title"
                        showHeader={false}
                    />
                </GuidanceDialog>
            )}

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

