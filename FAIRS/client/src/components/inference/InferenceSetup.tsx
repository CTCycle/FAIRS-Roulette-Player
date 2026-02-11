import React, { useEffect, useState, useRef } from 'react';
import type { GameConfig } from '../../types/inference';
import type { InferenceSetupState } from '../../context/AppStateContext';
import styles from './InferenceSetup.module.css';
import { Play } from 'lucide-react';

interface InferenceSetupProps {
    setup: InferenceSetupState;
    onSetupChange: (updates: Partial<InferenceSetupState>) => void;
    onStartSession: (config: GameConfig) => void;
}

export const InferenceSetup: React.FC<InferenceSetupProps> = ({
    setup,
    onSetupChange,
    onStartSession,
}) => {
    const { initialCapital, betAmount, checkpoint, datasetFileMetadata } = setup;

    // Keep actual File object in local state (not serializable for context)
    const [datasetFile, setDatasetFile] = useState<File | null>(null);
    const [checkpoints, setCheckpoints] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const latestCheckpointRef = useRef(checkpoint);

    useEffect(() => {
        latestCheckpointRef.current = checkpoint;
    }, [checkpoint]);

    useEffect(() => {
        const loadCheckpoints = async () => {
            try {
                const response = await fetch('/api/training/checkpoints');
                if (!response.ok) {
                    return;
                }
                const data = await response.json();
                if (Array.isArray(data)) {
                    setCheckpoints(data);
                    if (data.length > 0 && !latestCheckpointRef.current) {
                        onSetupChange({ checkpoint: String(data[0]) });
                    }
                }
            } catch (err) {
                console.error('Failed to load checkpoints:', err);
            }
        };

        loadCheckpoints();
    }, [onSetupChange]);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            setDatasetFile(file);
            onSetupChange({
                datasetFileMetadata: {
                    name: file.name,
                    size: file.size,
                    type: file.type,
                },
            });
            setError(null);
        }
    };

    const uploadDataset = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/data/upload?table=inference_context', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const payload = await response.json().catch(() => null);
            const detail = payload && typeof payload === 'object' && 'detail' in payload ? String(payload.detail) : 'Upload failed.';
            throw new Error(detail);
        }
        return await response.json();
    };

    const startSession = async (datasetId: string) => {
        const resolvedDatasetId = Number(datasetId);
        if (!Number.isInteger(resolvedDatasetId) || resolvedDatasetId <= 0) {
            throw new Error('Invalid dataset identifier.');
        }
        const startPayload = {
            checkpoint,
            dataset_id: resolvedDatasetId,
            game_capital: initialCapital,
            game_bet: betAmount,
        };
        console.info('[Inference] Starting session request', startPayload);

        const response = await fetch('/api/inference/sessions/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(startPayload),
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
            const uploadPayload = await uploadDataset(datasetFile);
            const datasetId = String(
                (uploadPayload as { dataset_id?: unknown }).dataset_id ?? ''
            );
            if (!datasetId) {
                throw new Error('Upload completed but dataset_id was not returned.');
            }
            const session = await startSession(datasetId);

            onStartSession({
                initialCapital,
                betAmount,
                checkpoint,
                datasetName: datasetId,
                sessionId: String(session.session_id),
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
                    onChange={(e) => onSetupChange({ checkpoint: e.target.value })}
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
                    onChange={(e) => onSetupChange({ initialCapital: Number(e.target.value) })}
                    min="1"
                />
            </div>

            <div className={styles.formGroup}>
                <label className={styles.label}>Bet Amount (€)</label>
                <input
                    type="number"
                    className={styles.input}
                    value={betAmount}
                    onChange={(e) => onSetupChange({ betAmount: Number(e.target.value) })}
                    min="1"
                />
            </div>

            <div className={styles.formGroup}>
                <label className={styles.label}>Inference Context (Dataset)</label>
                <div className={styles.fileInputWrapper}>
                    <input
                        type="file"
                        ref={fileInputRef}
                        accept=".csv,.xlsx"
                        onChange={handleFileChange}
                        className={styles.input}
                        style={{ width: '100%' }}
                    />
                </div>
                {(datasetFile || datasetFileMetadata) && (
                    <span className={styles.uploadedFile}>
                        Selected: {datasetFile?.name || datasetFileMetadata?.name}
                    </span>
                )}
            </div>

            {error && (
                <div style={{ marginTop: '0.5rem', color: 'var(--danger, #ff6b6b)' }}>
                    {error}
                </div>
            )}

            <button
                className={styles.button}
                onClick={handleStart}
                disabled={(!datasetFile && !datasetFileMetadata) || !checkpoint || isLoading}
            >
                <Play size={20} />
                {isLoading ? 'Starting...' : 'Start Session'}
            </button>
        </div>
    );
};
