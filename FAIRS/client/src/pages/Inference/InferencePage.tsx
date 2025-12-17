import React, { useState } from 'react';
import { InferenceSetup } from '../../components/inference/InferenceSetup';
import { GameSession } from '../../components/inference/GameSession';
import type { GameConfig } from '../../types/inference';

const InferencePage: React.FC = () => {
    const [gameConfig, setGameConfig] = useState<GameConfig | null>(null);

    const handleStartSession = (config: GameConfig) => {
        setGameConfig(config);
    };

    return (
        <div style={{ height: '100%', padding: '1rem' }}>
            {!gameConfig ? (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                    <InferenceSetup onStartSession={handleStartSession} />
                </div>
            ) : (
                <GameSession config={gameConfig} />
            )}
        </div>
    );
};

export default InferencePage;
