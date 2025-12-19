import React, { useState } from 'react';
import { useAppState } from '../../context/AppStateContext';
import './Training.css';
import { TrainingControls } from './components/TrainingControls';
import { TrainingDashboard } from './components/TrainingDashboard';

const TrainingPage: React.FC = () => {
    const { state, dispatch } = useAppState();
    const { isTraining, newConfig, resumeConfig } = state.training;
    const [datasetRefreshKey] = useState(0);

    const setIsTraining = (value: boolean) => {
        dispatch({ type: 'SET_TRAINING_IS_TRAINING', payload: value });
    };

    return (
        <div className="training-page">
            <div className="page-header">
                <h1 className="page-title">Training Dashboard</h1>
            </div>

            <div className="training-content">
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

