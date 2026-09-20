import React from 'react';
import RouletteWheel from './RouletteWheel';
import type { BackendStartupStatus } from '../../types/startup';
import './StartupScreen.css';

interface StartupScreenProps {
    status: BackendStartupStatus;
    elapsedSeconds: number;
    onRetry: () => void;
}

const StartupScreen: React.FC<StartupScreenProps> = ({
    status,
    elapsedSeconds,
    onRetry,
}) => {
    const isWaiting = status === 'waiting';
    const isSlow = isWaiting && elapsedSeconds >= 15;

    return (
        <main
            className={`startup-screen startup-screen--${status}`}
            data-testid="startup-screen"
            aria-busy={isWaiting}
        >
            <div className="startup-screen__ambient startup-screen__ambient--left" aria-hidden="true" />
            <div className="startup-screen__ambient startup-screen__ambient--right" aria-hidden="true" />
            <section
                className="startup-screen__content"
                role={isWaiting ? 'status' : 'alert'}
                aria-live="polite"
            >
                <div className="startup-screen__brand" aria-label="FAIRS Roulette Player">
                    <span className="startup-screen__brand-title">FAIRS</span>
                    <span className="startup-screen__brand-subtitle">Roulette Player</span>
                </div>

                <RouletteWheel paused={!isWaiting} />

                <div className="startup-screen__copy">
                    <p className="startup-screen__message">
                        {isWaiting ? 'Preparing the table…' : 'The table is taking a break.'}
                    </p>
                    <p className="startup-screen__detail">
                        {isWaiting
                            ? (isSlow
                                ? 'The backend is taking a little longer than usual.'
                                : 'Starting the FAIRS backend.')
                            : 'FAIRS could not connect to its backend. Check that the launcher is still running, then try again.'}
                    </p>
                </div>

                {isWaiting ? (
                    <div className="startup-screen__status-line">
                        <span className="startup-screen__status-dot" aria-hidden="true" />
                        <span>Waiting for a healthy response</span>
                    </div>
                ) : (
                    <button
                        type="button"
                        className="startup-screen__retry"
                        data-testid="startup-retry"
                        onClick={onRetry}
                    >
                        Retry connection
                    </button>
                )}
            </section>
        </main>
    );
};

export default StartupScreen;
