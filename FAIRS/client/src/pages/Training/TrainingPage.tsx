import React from 'react';
import './Training.css';
import { DatasetUpload } from './components/DatasetUpload';
import { TrainingControls } from './components/TrainingControls';

const TrainingPage: React.FC = () => {
    return (
        <div className="training-page">
            <div className="page-header">
                <h1 className="page-title">Training Dashboard</h1>
            </div>

            <div className="training-content">
                <DatasetUpload />
                <TrainingControls />
            </div>
        </div>
    );
};

export default TrainingPage;
