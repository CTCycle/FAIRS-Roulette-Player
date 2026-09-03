import React, { useCallback, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { DecisionInspector } from '../../components/inference/DecisionInspector';
import { GameSession } from '../../components/inference/GameSession';
import type {
    InferenceSessionSnapshot,
    InferenceSetupState,
} from '../../types/inference';
import './InferencePage.css';

interface InferenceNavigationState {
    inferenceSetup?: Partial<InferenceSetupState>;
}

const initialSetup: InferenceSetupState = {
    initialCapital: 100,
    betAmount: 1,
    checkpoint: '',
    selectedDataset: null,
    uploadedDatasetId: null,
    datasetFileMetadata: null,
};

const createInitialSnapshot = (setup: InferenceSetupState): InferenceSessionSnapshot => ({
    config: null,
    isActive: false,
    currentCapital: setup.initialCapital,
    currentBet: setup.betAmount,
    lastPrediction: null,
    totalSteps: 0,
    history: [],
});

const InferencePage: React.FC = () => {
    const location = useLocation();
    const navigationSetup = (location.state as InferenceNavigationState | null)?.inferenceSetup;
    const resolvedInitialSetup = { ...initialSetup, ...navigationSetup };
    const [setup, setSetup] = useState<InferenceSetupState>(resolvedInitialSetup);
    const [snapshot, setSnapshot] = useState<InferenceSessionSnapshot>(
        () => createInitialSnapshot(resolvedInitialSetup),
    );

    const handleSetupChange = useCallback((updates: Partial<InferenceSetupState>) => {
        setSetup((current) => ({ ...current, ...updates }));
    }, []);

    const handleSnapshotChange = useCallback((updates: Partial<InferenceSessionSnapshot>) => {
        setSnapshot((current) => ({ ...current, ...updates }));
    }, []);

    return (
        <div className="inference-page page-shell">
            <div className="page-header">
                <p className="page-subtitle">
                    Pair a trained checkpoint with a dataset, step through predictions, and inspect session history in real time.
                </p>
            </div>

            <div className="inference-workspace">
                <GameSession
                    setup={setup}
                    snapshot={snapshot}
                    onSetupChange={handleSetupChange}
                    onSnapshotChange={handleSnapshotChange}
                />
                <DecisionInspector
                    prediction={snapshot.lastPrediction}
                    history={snapshot.history}
                    currentBet={snapshot.currentBet}
                />
            </div>
        </div>
    );
};

export default InferencePage;
