import React, { useState } from 'react';
import './Training.css';
import { DatasetUpload } from './components/DatasetUpload';
import { TrainingControls } from './components/TrainingControls';
import { TrainingDashboard } from './components/TrainingDashboard';

const TrainingPage: React.FC = () => {
    const [isTraining, setIsTraining] = useState(false);

    return (
        <div className="training-page">
            <div className="page-header">
                <h1 className="page-title">Training Dashboard</h1>
            </div>

            <div className="training-content">
                <DatasetUpload />
                <TrainingControls onTrainingStart={() => setIsTraining(true)} />
            </div>

            <TrainingDashboard isActive={isTraining} />
        </div>
    );
};

export default TrainingPage;
