import React, { useEffect, useState } from 'react';
import type { GameConfig } from '../../types/inference';
import styles from './InferenceSetup.module.css';
import { Play } from 'lucide-react';

interface InferenceSetupProps {
    onStartSession: (config: GameConfig) => void;
}

export const InferenceSetup: React.FC<InferenceSetupProps> = ({ onStartSession }) => {
    const [initialCapital, setInitialCapital] = useState<number>(100);
    const [betAmount, setBetAmount] = useState<number>(1);
    const [checkpoint, setCheckpoint] = useState<string>('');
    const [datasetFile, setDatasetFile] = useState<File | null>(null);
    const [checkpoints, setCheckpoints] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadCheckpoints = async () => {
            try {
                const response = await fetch('/training/checkpoints');
                if (!response.ok) {
                    return;
                }
                const data = await response.json();
                if (Array.isArray(data)) {
                    setCheckpoints(data);
                    if (data.length > 0) {
                        setCheckpoint(String(data[0]));
                    }
                }
            } catch (err) {
                console.error('Failed to load checkpoints:', err);
            }
        };

        loadCheckpoints();
    }, []);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setDatasetFile(e.target.files[0]);
            setError(null);
        }
    };

    const uploadDataset = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/data/upload?table=PREDICTED_GAMES', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const payload = await response.json().catch(() => null);
            const detail = payload && typeof payload === 'object' && 'detail' in payload ? String(payload.detail) : 'Upload failed.';
            throw new Error(detail);
        }
    };

    const startSession = async () => {
        const response = await fetch('/inference/sessions/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                checkpoint,
                game_capital: initialCapital,
                game_bet: betAmount,
            }),
        });

        if (!response.ok) {
            const payload = await response.json().catch(() => null);
            const detail = payload && typeof payload === 'object' && 'detail' in payload ? String(payload.detail) : 'Session start failed.';
            throw new Error(detail);
        }

        return await response.json();
    };

    const handleStart = async () => {
        if (!datasetFile) {
            setError('Select an inference dataset first.');
            return;
        }
        if (!checkpoint) {
            setError('Select a checkpoint first.');
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            await uploadDataset(datasetFile);
            const session = await startSession();

            onStartSession({
                initialCapital,
                betAmount,
                checkpoint,
                datasetName: datasetFile.name,
                sessionId: String(session.session_id),
                initialPrediction: session.prediction,
            });
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unable to start session.';
            setError(message);
        } finally {
            setIsLoading(false);
        }
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
                    disabled={checkpoints.length === 0}
                >
                    {checkpoints.length === 0 ? (
                        <option value="">No checkpoints found</option>
                    ) : (
                        checkpoints.map((cp) => (
                            <option key={cp} value={cp}>{cp}</option>
                        ))
                    )}
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
                {datasetFile && (
                    <span className={styles.uploadedFile}>Selected: {datasetFile.name}</span>
                )}
            </div>

            {error && (
                <div style={{ marginTop: '0.5rem', color: 'var(--danger, #ff6b6b)' }}>
                    {error}
                </div>
            )}

            <button className={styles.button} onClick={handleStart} disabled={!datasetFile || !checkpoint || isLoading}>
                <Play size={20} />
                {isLoading ? 'Starting...' : 'Start Session'}
            </button>
        </div>
    );
};
