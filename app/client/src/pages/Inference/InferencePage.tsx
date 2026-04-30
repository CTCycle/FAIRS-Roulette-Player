import React, { useCallback } from 'react';
import { useAppState } from '../../hooks/useAppState';
import { GameSession } from '../../components/inference/GameSession';
import type { GameConfig, SessionState, GameStep } from '../../types/inference';
import './InferencePage.css';

const InferencePage: React.FC = () => {
    const { state, dispatch } = useAppState();
    const { gameConfig, setup, sessionState, history } = state.inference;

    const handleSessionStateChange = useCallback((updates: Partial<SessionState>) => {
        dispatch({ type: 'SET_INFERENCE_SESSION_STATE', payload: updates });
    }, [dispatch]);

    const handleAddHistoryStep = useCallback((step: GameStep) => {
        dispatch({ type: 'ADD_INFERENCE_HISTORY_STEP', payload: step });
    }, [dispatch]);

    const handleHistoryChange = useCallback((steps: GameStep[]) => {
        dispatch({ type: 'SET_INFERENCE_HISTORY', payload: steps });
    }, [dispatch]);

    const handleGameConfigChange = useCallback((config: GameConfig | null) => {
        dispatch({ type: 'SET_INFERENCE_GAME_CONFIG', payload: config });
    }, [dispatch]);

    const handleSetupChange = useCallback((updates: Partial<typeof setup>) => {
        dispatch({ type: 'SET_INFERENCE_SETUP', payload: updates });
    }, [dispatch]);

    const handleClearSession = useCallback(() => {
        dispatch({ type: 'RESET_INFERENCE_SESSION' });
    }, [dispatch]);

    return (
        <div className="inference-page page-shell">
            <div className="page-header">
                <h1 className="page-title">Inference Workspace</h1>
                <p className="page-subtitle">
                    Pair a trained checkpoint with a dataset, step through predictions, and inspect session history in real time.
                </p>
            </div>

            <div className="inference-workspace">
                <GameSession
                    config={gameConfig}
                    setup={setup}
                    sessionState={sessionState}
                    history={history}
                    onSetupChange={handleSetupChange}
                    onSessionStateChange={handleSessionStateChange}
                    onAddHistoryStep={handleAddHistoryStep}
                    onHistoryChange={handleHistoryChange}
                    onGameConfigChange={handleGameConfigChange}
                    onClearSession={handleClearSession}
                />
            </div>
        </div>
    );
};

export default InferencePage;

