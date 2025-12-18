import React, { useState } from 'react';
import type { GameConfig, SessionState, GameStep } from '../../types/inference';
import styles from './GameSession.module.css';
import { Check, History, X } from 'lucide-react';

interface GameSessionProps {
    config: GameConfig;
    sessionState: SessionState;
    history: GameStep[];
    onSessionStateChange: (updates: Partial<SessionState>) => void;
    onAddHistoryStep: (step: GameStep) => void;
    onEndSession: () => void;
}

export const GameSession: React.FC<GameSessionProps> = ({
    config,
    sessionState,
    history,
    onSessionStateChange,
    onAddHistoryStep,
    onEndSession,
}) => {
    const [realExtraction, setRealExtraction] = useState<string>('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const cleanNum = (val: string) => {
        // allow only 0-36
        const num = parseInt(val);
        if (val === '') return '';
        if (isNaN(num)) return '';
        if (num < 0) return '0';
        if (num > 36) return '36';
        return String(num);
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (realExtraction === '') return;

        const extraction = parseInt(realExtraction);
        setIsSubmitting(true);
        setError(null);

        try {
            const response = await fetch(`/api/inference/sessions/${config.sessionId}/step`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ extraction }),
            });

            if (!response.ok) {
                const payload = await response.json().catch(() => null);
                const detail = payload && typeof payload === 'object' && 'detail' in payload ? String(payload.detail) : 'Step failed.';
                throw new Error(detail);
            }

            const result = await response.json();
            const newCapital = Number(result.capital_after);
            const outcome = Number(result.reward);
            const step: GameStep = {
                step: Number(result.step),
                realExtraction: Number(result.real_extraction),
                predictedAction: Number(result.predicted_action),
                predictedActionDesc: String(result.predicted_action_desc),
                betAmount: sessionState.currentBet,
                outcome,
                capitalAfter: newCapital,
                timestamp: new Date().toLocaleTimeString(),
            };

            // Update session state via global context
            onSessionStateChange({
                currentCapital: newCapital,
                totalSteps: Number(result.step),
                lastPrediction: result.next_prediction,
            });

            // Add history step via global context
            onAddHistoryStep(step);

            setRealExtraction('');
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unable to submit step.';
            setError(message);
        } finally {
            setIsSubmitting(false);
        }
    };

    // Use history from props, but reverse for display (newest first)
    const displayHistory = [...history].reverse().slice(0, 50);

    return (
        <div className={styles.sessionContainer}>
            <div className={styles.leftPanel}>
                {/* Stats Card */}
                <div className={styles.card}>
                    <div className={styles.statGrid}>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Current Capital</span>
                            <span className={styles.statValue} style={{ color: 'var(--primary-accent)' }}>
                                € {sessionState.currentCapital.toFixed(2)}
                            </span>
                        </div>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Profit/Loss</span>
                            <span className={`${styles.statValue} ${sessionState.currentCapital >= config.initialCapital ? styles.outcomeWin : styles.outcomeLoss}`}>
                                {(sessionState.currentCapital - config.initialCapital) >= 0 ? '+' : ''}
                                € {(sessionState.currentCapital - config.initialCapital).toFixed(2)}
                            </span>
                        </div>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Bet Amount</span>
                            <span className={styles.statValue}>€ {sessionState.currentBet}</span>
                        </div>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Steps</span>
                            <span className={styles.statValue}>{sessionState.totalSteps}</span>
                        </div>
                    </div>
                </div>

                {/* Prediction Display */}
                <div className={styles.predictionCard}>
                    <div className={styles.predictionTitle}>AI Suggestion</div>
                    <div className={styles.predictionValue}>
                        {sessionState.lastPrediction?.description}
                    </div>
                    {sessionState.lastPrediction?.confidence && (
                        <div className={styles.predictionDesc}>
                            Confidence: {(sessionState.lastPrediction.confidence * 100).toFixed(0)}%
                        </div>
                    )}
                </div>

                {/* Input Form */}
                <div className={styles.card}>
                    <form onSubmit={handleSubmit}>
                        <div className={styles.inputGroup}>
                            <div style={{ flex: 1 }}>
                                <label className={styles.statLabel} style={{ display: 'block', marginBottom: '8px' }}>
                                    Real Extraction (0-36)
                                </label>
                                <input
                                    type="text"
                                    className={styles.numberInput}
                                    value={realExtraction}
                                    onChange={(e) => setRealExtraction(cleanNum(e.target.value))}
                                    autoFocus
                                />
                            </div>
                            <button type="submit" className={styles.submitBtn} disabled={realExtraction === '' || isSubmitting}>
                                <Check /> Submit Result
                            </button>
                        </div>
                        {error && (
                            <div style={{ marginTop: '0.75rem', color: 'var(--danger, #ff6b6b)' }}>
                                {error}
                            </div>
                        )}
                    </form>
                    <button
                        type="button"
                        className={styles.endSessionBtn}
                        onClick={onEndSession}
                    >
                        <X size={18} /> End Session
                    </button>
                </div>
            </div>

            <div className={styles.rightPanel}>
                <div className={styles.card} style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    <h3 className={styles.statLabel} style={{ fontSize: '1rem', marginBottom: '1rem', display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <History size={16} /> Session History
                    </h3>
                    <div style={{ overflowY: 'auto', flex: 1 }}>
                        <table className={styles.historyTable}>
                            <thead>
                                <tr>
                                    <th>Step</th>
                                    <th>Ext</th>
                                    <th>Prediction</th>
                                    <th>Outcome</th>
                                    <th>Capital</th>
                                </tr>
                            </thead>
                            <tbody>
                                {displayHistory.map((step) => (
                                    <tr key={step.step}>
                                        <td>#{step.step}</td>
                                        <td style={{ fontWeight: 'bold' }}>{step.realExtraction}</td>
                                        <td>{step.predictedActionDesc}</td>
                                        <td className={step.outcome >= 0 ? styles.outcomeWin : styles.outcomeLoss}>
                                            {step.outcome >= 0 ? '+' : ''}{step.outcome}
                                        </td>
                                        <td>{step.capitalAfter.toFixed(2)}</td>
                                    </tr>
                                ))}
                                {displayHistory.length === 0 && (
                                    <tr>
                                        <td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                                            No history yet. Start playing!
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};
