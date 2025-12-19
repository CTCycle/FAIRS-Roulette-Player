import React, { useState } from 'react';
import { useAppState } from '../../context/AppStateContext';
import './Training.css';
import { DatasetUpload } from './components/DatasetUpload';
import { TrainingControls } from './components/TrainingControls';
import { TrainingDashboard } from './components/TrainingDashboard';

const TrainingPage: React.FC = () => {
    const { state, dispatch } = useAppState();
    const { isTraining, datasetUpload, newConfig, resumeConfig } = state.training;
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
        if (updates.uploadStatus === 'success') {
            setDatasetRefreshKey((prev) => prev + 1);
        }
    };

    return (
        <div className="training-page">
            <div className="page-header">
                <h1 className="page-title">Training Dashboard</h1>
            </div>

            <div className="training-content">
                <DatasetUpload
                    files={datasetUpload.files}
                    uploadStatus={datasetUpload.uploadStatus}
                    uploadMessage={datasetUpload.uploadMessage}
                    onStateChange={handleDatasetUploadStateChange}
                    onReset={() => dispatch({ type: 'RESET_DATASET_UPLOAD' })}
                />
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
