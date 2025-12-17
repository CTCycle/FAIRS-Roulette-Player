import React, { useState } from 'react';
import type { GameConfig, SessionState, GameStep } from '../../types/inference';
import styles from './GameSession.module.css';
import { Check, History } from 'lucide-react';

interface GameSessionProps {
    config: GameConfig;
}

export const GameSession: React.FC<GameSessionProps> = ({ config }) => {
    const [state, setState] = useState<SessionState>({
        isActive: true,
        currentCapital: config.initialCapital,
        currentBet: config.betAmount,
        history: [],
        lastPrediction: {
            action: 1, // Mock initial prediction (e.g., Red)
            description: 'Bet on Red',
            confidence: 0.75
        },
        totalSteps: 0
    });

    const [realExtraction, setRealExtraction] = useState<string>('');

    const cleanNum = (val: string) => {
        // allow only 0-36
        const num = parseInt(val);
        if (val === '') return '';
        if (isNaN(num)) return '';
        if (num < 0) return '0';
        if (num > 36) return '36';
        return String(num);
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (realExtraction === '') return;

        const extraction = parseInt(realExtraction);
        const prediction = state.lastPrediction;

        // Mock Win/Loss Logic (Simplified)
        // In a real app, this would check if extraction matches prediction.action logic
        // For now, let's say Action 1 = Red, Action 0 = Black (roughly even/odd for demo)
        const isWin = Math.random() > 0.5;
        const outcome = isWin ? state.currentBet : -state.currentBet;
        const newCapital = state.currentCapital + outcome;

        const step: GameStep = {
            step: state.totalSteps + 1,
            realExtraction: extraction,
            predictedAction: prediction?.action || 0,
            predictedActionDesc: prediction?.description || 'Unknown',
            betAmount: state.currentBet,
            outcome: outcome,
            capitalAfter: newCapital,
            timestamp: new Date().toLocaleTimeString()
        };

        // Mock Next Prediction
        const nextPredAction = Math.floor(Math.random() * 3); // 0, 1, 2
        const nextPredDesc = nextPredAction === 0 ? 'Bet on Black' : (nextPredAction === 1 ? 'Bet on Red' : 'Skip Bet');

        setState(prev => ({
            ...prev,
            currentCapital: newCapital,
            history: [step, ...prev.history].slice(0, 50), // keep last 50
            totalSteps: prev.totalSteps + 1,
            lastPrediction: {
                action: nextPredAction,
                description: nextPredDesc,
                confidence: 0.6 + Math.random() * 0.3
            }
        }));

        setRealExtraction('');
    };

    return (
        <div className={styles.sessionContainer}>
            <div className={styles.leftPanel}>
                {/* Stats Card */}
                <div className={styles.card}>
                    <div className={styles.statGrid}>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Current Capital</span>
                            <span className={styles.statValue} style={{ color: 'var(--primary-accent)' }}>
                                € {state.currentCapital.toFixed(2)}
                            </span>
                        </div>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Profit/Loss</span>
                            <span className={`${styles.statValue} ${state.currentCapital >= config.initialCapital ? styles.outcomeWin : styles.outcomeLoss}`}>
                                {(state.currentCapital - config.initialCapital) >= 0 ? '+' : ''}
                                € {(state.currentCapital - config.initialCapital).toFixed(2)}
                            </span>
                        </div>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Bet Amount</span>
                            <span className={styles.statValue}>€ {state.currentBet}</span>
                        </div>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Steps</span>
                            <span className={styles.statValue}>{state.totalSteps}</span>
                        </div>
                    </div>
                </div>

                {/* Prediction Display */}
                <div className={styles.predictionCard}>
                    <div className={styles.predictionTitle}>AI Suggestion</div>
                    <div className={styles.predictionValue}>
                        {state.lastPrediction?.description}
                    </div>
                    {state.lastPrediction?.confidence && (
                        <div className={styles.predictionDesc}>
                            Confidence: {(state.lastPrediction.confidence * 100).toFixed(0)}%
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
                                    type="text" // text to better control parsing
                                    className={styles.numberInput}
                                    value={realExtraction}
                                    onChange={(e) => setRealExtraction(cleanNum(e.target.value))}
                                    autoFocus
                                />
                            </div>
                            <button type="submit" className={styles.submitBtn} disabled={realExtraction === ''}>
                                <Check /> Submit Result
                            </button>
                        </div>
                    </form>
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
                                {state.history.map((step) => (
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
                                {state.history.length === 0 && (
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
