import React from 'react';
import { useAppState } from '../../context/AppStateContext';
import './Training.css';
import { DatasetUpload } from './components/DatasetUpload';
import { TrainingControls } from './components/TrainingControls';
import { TrainingDashboard } from './components/TrainingDashboard';

const TrainingPage: React.FC = () => {
    const { state, dispatch } = useAppState();
    const { isTraining, datasetUpload, newConfig, resumeConfig } = state.training;

    const setIsTraining = (value: boolean) => {
        dispatch({ type: 'SET_TRAINING_IS_TRAINING', payload: value });
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
                    onStateChange={(updates) =>
                        dispatch({ type: 'SET_DATASET_UPLOAD_STATE', payload: updates })
                    }
                    onReset={() => dispatch({ type: 'RESET_DATASET_UPLOAD' })}
                    newConfig={newConfig}
                    onNewConfigChange={(updates) =>
                        dispatch({ type: 'SET_TRAINING_NEW_CONFIG', payload: updates })
                    }
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
                />
            </div>

            <TrainingDashboard isActive={isTraining} onTrainingEnd={() => setIsTraining(false)} />
        </div>
    );
};

export default TrainingPage;
