import React, { useState } from 'react';
import type { GameConfig } from '../../types/inference';
import styles from './InferenceSetup.module.css';
import { Play } from 'lucide-react';

interface InferenceSetupProps {
    onStartSession: (config: GameConfig) => void;
}

const MOCK_CHECKPOINTS = [
    'checkpoint_v1_best.pt',
    'checkpoint_v2_experimental.pt',
    'checkpoint_final_production.pt',
];

export const InferenceSetup: React.FC<InferenceSetupProps> = ({ onStartSession }) => {
    const [initialCapital, setInitialCapital] = useState<number>(1000);
    const [betAmount, setBetAmount] = useState<number>(10);
    const [checkpoint, setCheckpoint] = useState<string>(MOCK_CHECKPOINTS[0]);
    const [datasetName, setDatasetName] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setDatasetName(e.target.files[0].name);
        }
    };

    const handleStart = () => {
        onStartSession({
            initialCapital,
            betAmount,
            checkpoint,
            datasetName,
        });
    };

    return (
        <div className={styles.container}>
            <h2 className={styles.title}>New Game Session</h2>

            <div className={styles.formGroup}>
                <label className={styles.label}>Model Checkpoint</label>
                <select
                    className={styles.select}
                    value={checkpoint}
                    onChange={(e) => setCheckpoint(e.target.value)}
                >
                    {MOCK_CHECKPOINTS.map((cp) => (
                        <option key={cp} value={cp}>{cp}</option>
                    ))}
                </select>
            </div>

            <div className={styles.formGroup}>
                <label className={styles.label}>Initial Capital (€)</label>
                <input
                    type="number"
                    className={styles.input}
                    value={initialCapital}
                    onChange={(e) => setInitialCapital(Number(e.target.value))}
                    min="1"
                />
            </div>

            <div className={styles.formGroup}>
                <label className={styles.label}>Bet Amount (€)</label>
                <input
                    type="number"
                    className={styles.input}
                    value={betAmount}
                    onChange={(e) => setBetAmount(Number(e.target.value))}
                    min="1"
                />
            </div>

            <div className={styles.formGroup}>
                <label className={styles.label}>Inference Context (Dataset)</label>
                <div className={styles.fileInputWrapper}>
                    <input
                        type="file"
                        accept=".csv,.xlsx"
                        onChange={handleFileChange}
                        className={styles.input}
                        style={{ width: '100%' }}
                    />
                </div>
                {datasetName && (
                    <span className={styles.uploadedFile}>Selected: {datasetName}</span>
                )}
            </div>

            <button className={styles.button} onClick={handleStart} disabled={!datasetName}>
                <Play size={20} />
                Start Session
            </button>
        </div>
    );
};
