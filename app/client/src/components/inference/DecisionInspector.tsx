import React, { useMemo } from 'react';
import { Activity, ListOrdered, Target } from 'lucide-react';

import type { GameStep, PredictionResult } from '../../types/inference';
import styles from './DecisionInspector.module.css';

interface DecisionInspectorProps {
    prediction: PredictionResult | null;
    history: GameStep[];
    currentBet: number;
}

export const DecisionInspector: React.FC<DecisionInspectorProps> = ({
    prediction,
    history,
    currentBet,
}) => {
    const recentObserved = useMemo(
        () => history
            .filter((step) => step.observed !== null)
            .slice(-12)
            .map((step) => step.observed as number),
        [history],
    );

    if (!prediction && recentObserved.length === 0) {
        return null;
    }

    return (
        <section className={styles.inspector} aria-labelledby="decision-inspector-title">
            <div className={styles.header}>
                <div>
                    <div className={styles.eyebrow}>Research context</div>
                    <h3 id="decision-inspector-title" className={styles.title}>Decision Inspector</h3>
                </div>
                <Activity size={20} aria-hidden="true" />
            </div>

            <div className={styles.grid}>
                <div className={styles.detail}>
                    <div className={styles.detailLabel}><Target size={15} /> Agent decision</div>
                    <div className={styles.detailValue}>{prediction?.description ?? 'No active prediction'}</div>
                    {prediction?.relativePreference !== undefined && (
                        <div className={styles.preference}>
                            <span>Relative Q preference</span>
                            <strong>{(prediction.relativePreference * 100).toFixed(1)}%</strong>
                        </div>
                    )}
                    {prediction?.relativePreference !== undefined && (
                        <p className={styles.hint}>
                            Normalized preference derived from the action Q-scores. It is not a calibrated probability of success.
                        </p>
                    )}
                    <div className={styles.metaRow}>
                        <span>Current bet</span>
                        <strong>€ {currentBet}</strong>
                    </div>
                    {prediction?.betStrategyName && (
                        <div className={styles.metaRow}>
                            <span>Bet strategy</span>
                            <strong>{prediction.betStrategyName}</strong>
                        </div>
                    )}
                </div>

                <div className={styles.detail}>
                    <div className={styles.detailLabel}><ListOrdered size={15} /> Recent observed sequence</div>
                    {recentObserved.length === 0 ? (
                        <div className={styles.empty}>Observed outcomes will appear after confirmed rounds.</div>
                    ) : (
                        <div className={styles.sequence} aria-label="Recent observed roulette sequence">
                            {recentObserved.map((value, index) => (
                                <span key={`${index}-${value}`} className={styles.sequenceValue}>{value}</span>
                            ))}
                        </div>
                    )}
                    <p className={styles.hint}>
                        This compact strip shows confirmed observations from the current session and helps relate recent sequence context to the active decision.
                    </p>
                </div>
            </div>
        </section>
    );
};
