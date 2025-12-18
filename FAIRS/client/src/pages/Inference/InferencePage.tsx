import React from 'react';
import { useAppState } from '../../context/AppStateContext';
import { InferenceSetup } from '../../components/inference/InferenceSetup';
import { GameSession } from '../../components/inference/GameSession';
import type { GameConfig, SessionState, GameStep } from '../../types/inference';

const InferencePage: React.FC = () => {
    const { state, dispatch } = useAppState();
    const { gameConfig, setup, sessionState, history } = state.inference;

    const handleStartSession = (config: GameConfig) => {
        dispatch({ type: 'SET_INFERENCE_GAME_CONFIG', payload: config });
        dispatch({
            type: 'SET_INFERENCE_SESSION_STATE',
            payload: {
                isActive: true,
                currentCapital: config.initialCapital,
                currentBet: config.betAmount,
                lastPrediction: config.initialPrediction,
                totalSteps: 0,
            },
        });
    };

    const handleSessionStateChange = (updates: Partial<SessionState>) => {
        dispatch({ type: 'SET_INFERENCE_SESSION_STATE', payload: updates });
    };

    const handleAddHistoryStep = (step: GameStep) => {
        dispatch({ type: 'ADD_INFERENCE_HISTORY_STEP', payload: step });
    };

    return (
        <div style={{ height: '100%', padding: '2rem' }}>
            {!gameConfig ? (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                    <InferenceSetup
                        setup={setup}
                        onSetupChange={(updates) =>
                            dispatch({ type: 'SET_INFERENCE_SETUP', payload: updates })
                        }
                        onStartSession={handleStartSession}
                    />
                </div>
            ) : (
                <GameSession
                    config={gameConfig}
                    sessionState={sessionState}
                    history={history}
                    onSessionStateChange={handleSessionStateChange}
                    onAddHistoryStep={handleAddHistoryStep}
                    onEndSession={() => dispatch({ type: 'RESET_INFERENCE_SESSION' })}
                />
            )}
        </div>
    );
};

export default InferencePage;
