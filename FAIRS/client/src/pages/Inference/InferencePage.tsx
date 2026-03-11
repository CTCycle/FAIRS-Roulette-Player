import React from 'react';
import { useAppState } from '../../hooks/useAppState';
import { GameSession } from '../../components/inference/GameSession';
import type { GameConfig, SessionState, GameStep } from '../../types/inference';
import './InferencePage.css';

const InferencePage: React.FC = () => {
    const { state, dispatch } = useAppState();
    const { gameConfig, setup, sessionState, history } = state.inference;

    const handleSessionStateChange = (updates: Partial<SessionState>) => {
        dispatch({ type: 'SET_INFERENCE_SESSION_STATE', payload: updates });
    };

    const handleAddHistoryStep = (step: GameStep) => {
        dispatch({ type: 'ADD_INFERENCE_HISTORY_STEP', payload: step });
    };

    const handleHistoryChange = (steps: GameStep[]) => {
        dispatch({ type: 'SET_INFERENCE_HISTORY', payload: steps });
    };

    const handleGameConfigChange = (config: GameConfig | null) => {
        dispatch({ type: 'SET_INFERENCE_GAME_CONFIG', payload: config });
    };

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
                    onSetupChange={(updates) =>
                        dispatch({ type: 'SET_INFERENCE_SETUP', payload: updates })
                    }
                    onSessionStateChange={handleSessionStateChange}
                    onAddHistoryStep={handleAddHistoryStep}
                    onHistoryChange={handleHistoryChange}
                    onGameConfigChange={handleGameConfigChange}
                    onClearSession={() => dispatch({ type: 'RESET_INFERENCE_SESSION' })}
                />
            </div>
        </div>
    );
};

export default InferencePage;

