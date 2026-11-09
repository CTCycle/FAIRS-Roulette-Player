// Copyright © 2023 Thomas Virdis
// Licensed under the MIT License.

import React, { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { GameSession } from '../../components/inference/GameSession';
import { INFERENCE_START_REQUEST_DEFAULTS } from '../../generated/api';
import type {
    InferenceSessionSnapshot,
    InferenceSetupState,
} from '../../types/inference';
import './InferencePage.css';

interface InferenceNavigationState {
    inferenceSetup?: Partial<InferenceSetupState>;
}

const initialSetup: InferenceSetupState = {
    initialCapital: INFERENCE_START_REQUEST_DEFAULTS.game_capital,
    betAmount: INFERENCE_START_REQUEST_DEFAULTS.game_bet,
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

// Page state is retained across route changes (the page unmounts on navigation),
// so recorded history and parameters survive visiting other pages.
const retained: {
    setup: InferenceSetupState | null;
    snapshot: InferenceSessionSnapshot | null;
} = { setup: null, snapshot: null };

const InferencePage: React.FC = () => {
    const location = useLocation();
    const navigationSetup = (location.state as InferenceNavigationState | null)?.inferenceSetup;
    const [setup, setSetup] = useState<InferenceSetupState>(
        () => ({ ...(retained.setup ?? initialSetup), ...navigationSetup }),
    );
    const [snapshot, setSnapshot] = useState<InferenceSessionSnapshot>(
        () => retained.snapshot ?? createInitialSnapshot({ ...initialSetup, ...navigationSetup }),
    );

    useEffect(() => {
        retained.setup = setup;
        retained.snapshot = snapshot;
    }, [setup, snapshot]);

    const handleSetupChange = useCallback((updates: Partial<InferenceSetupState>) => {
        setSetup((current) => ({ ...current, ...updates }));
    }, []);

    const handleSnapshotChange = useCallback((updates: Partial<InferenceSessionSnapshot>) => {
        setSnapshot((current) => ({ ...current, ...updates }));
    }, []);

    return (
        <div className="inference-page page-shell">
            <div className="inference-workspace">
                <GameSession
                    setup={setup}
                    snapshot={snapshot}
                    onSetupChange={handleSetupChange}
                    onSnapshotChange={handleSnapshotChange}
                />
            </div>
        </div>
    );
};

export default InferencePage;
