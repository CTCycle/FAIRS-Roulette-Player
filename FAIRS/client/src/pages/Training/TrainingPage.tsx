import React, { useState } from 'react';
import { useAppState } from '../../context/AppStateContext';
import './Training.css';
import { TrainingControls } from './components/TrainingControls';
import { TrainingDashboard } from './components/TrainingDashboard';
import { DatasetUpload } from './components/DatasetUpload';
import { DatasetPreview } from './components/DatasetPreview';
import { CheckpointPreview } from './components/CheckpointPreview';

const TrainingPage: React.FC = () => {
    const { state, dispatch } = useAppState();
    const { isTraining, newConfig, resumeConfig, datasetUpload } = state.training;
    const [datasetRefreshKey, setDatasetRefreshKey] = useState(0);

    const setIsTraining = (value: boolean) => {
        dispatch({ type: 'SET_TRAINING_IS_TRAINING', payload: value });
    };

    const handleDatasetUploadStateChange = (updates: {
        files?: typeof datasetUpload.files;
        uploadStatus?: typeof datasetUpload.uploadStatus;
        uploadMessage?: string;
    }) => {
        dispatch({ type: 'SET_DATASET_UPLOAD_STATE', payload: updates });
    };

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
                {/* Upload Widget */}
                <DatasetUpload
                    files={datasetUpload.files}
                    uploadStatus={datasetUpload.uploadStatus}
                    uploadMessage={datasetUpload.uploadMessage}
                    onStateChange={handleDatasetUploadStateChange}
                    onReset={() => dispatch({ type: 'RESET_DATASET_UPLOAD' })}
                    onUploadSuccess={handleUploadSuccess}
                />

                {/* Preview Row: Datasets (Left) | Checkpoints (Right) */}
                <div className="preview-row">
                    <DatasetPreview
                        refreshKey={datasetRefreshKey}
                        onDelete={handleDatasetDelete}
                    />
                    <CheckpointPreview refreshKey={datasetRefreshKey} />
                </div>

                <TrainingControls
                    newConfig={newConfig}
                    resumeConfig={resumeConfig}
                    onNewConfigChange={(updates) =>
                        dispatch({ type: 'SET_TRAINING_NEW_CONFIG', payload: updates })
                    }
                    onResumeConfigChange={(updates) =>
                        dispatch({ type: 'SET_TRAINING_RESUME_CONFIG', payload: updates })
                    }
                    onTrainingStart={() => setIsTraining(true)}
                    datasetRefreshKey={datasetRefreshKey}
                />
            </div>

            <TrainingDashboard isActive={isTraining} onTrainingEnd={() => setIsTraining(false)} />
        </div>
    );
};

export default TrainingPage;
