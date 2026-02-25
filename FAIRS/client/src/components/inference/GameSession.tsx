import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { GameConfig, GameStep, PredictionResult, SessionState } from '../../types/inference';
import type { InferenceSetupState } from '../../context/AppStateContext';
import styles from './GameSession.module.css';
import { Check, History, Pencil, Play, Square, Trash2 } from 'lucide-react';

interface DatasetOption {
    dataset_id: string;
    dataset_name: string;
}

const parseDatasetId = (value: unknown): string => {
    if (typeof value === 'number' && Number.isInteger(value) && value > 0) {
        return String(value);
    }
    if (typeof value === 'string') {
        const trimmed = value.trim();
        if (/^\d+$/.test(trimmed)) {
            return trimmed;
        }
    }
    return '';
};

interface GameSessionProps {
    config: GameConfig | null;
    setup: InferenceSetupState;
    sessionState: SessionState;
    history: GameStep[];
    onSetupChange: (updates: Partial<InferenceSetupState>) => void;
    onSessionStateChange: (updates: Partial<SessionState>) => void;
    onAddHistoryStep: (step: GameStep) => void;
    onHistoryChange: (steps: GameStep[]) => void;
    onGameConfigChange: (config: GameConfig | null) => void;
    onClearSession: () => void;
}

const cleanObserved = (val: string) => {
    if (val === '') return '';
    const num = parseInt(val, 10);
    if (Number.isNaN(num)) return '';
    if (num < 0) return '0';
    if (num > 36) return '36';
    return String(num);
};

const maybeNumber = (value: unknown): number | undefined => {
    if (value === null || value === undefined || value === '') {
        return undefined;
    }
    if (typeof value === 'boolean') {
        return undefined;
    }
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
        return undefined;
    }
    return parsed;
};

const normalizePrediction = (value: unknown): PredictionResult => {
    const payload = (typeof value === 'object' && value !== null ? value : {}) as Record<string, unknown>;
    const action = maybeNumber(payload.action) ?? 0;
    const description = typeof payload.description === 'string' ? payload.description : 'Unknown';
    const confidence = maybeNumber(payload.confidence);
    const betStrategyId = maybeNumber(payload.bet_strategy_id ?? payload.betStrategyId);
    const betStrategyName = typeof payload.bet_strategy_name === 'string'
        ? payload.bet_strategy_name
        : (typeof payload.betStrategyName === 'string' ? payload.betStrategyName : undefined);
    const suggestedBetAmount = maybeNumber(payload.suggested_bet_amount ?? payload.suggestedBetAmount);
    const currentBetAmount = maybeNumber(payload.current_bet_amount ?? payload.currentBetAmount);

    return {
        action,
        description,
        confidence,
        betStrategyId,
        betStrategyName,
        suggestedBetAmount,
        currentBetAmount,
    };
};

export const GameSession: React.FC<GameSessionProps> = ({
    config,
    setup,
    sessionState,
    history,
    onSetupChange,
    onSessionStateChange,
    onAddHistoryStep,
    onHistoryChange,
    onGameConfigChange,
    onClearSession,
}) => {
    const [checkpoints, setCheckpoints] = useState<string[]>([]);
    const [datasets, setDatasets] = useState<DatasetOption[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [isStarting, setIsStarting] = useState(false);
    const [isStopping, setIsStopping] = useState(false);
    const [isRecomputing, setIsRecomputing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const latestSetupRef = useRef(setup);

    const sessionActive = sessionState.isActive;
    const datasetLocked = sessionActive || setup.datasetSource === 'uploaded';
    const setupLocked = sessionActive;

    const datasetId = useMemo(() => {
        if (setup.datasetSource === 'uploaded') {
            return setup.uploadedDatasetName;
        }
        return setup.selectedDataset;
    }, [setup.datasetSource, setup.selectedDataset, setup.uploadedDatasetName]);

    useEffect(() => {
        latestSetupRef.current = setup;
    }, [setup]);

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
                    if (data.length > 0 && !latestSetupRef.current.checkpoint) {
                        onSetupChange({ checkpoint: String(data[0]) });
                    }
                }
            } catch (err) {
                console.error('Failed to load checkpoints:', err);
            }
        };

        const loadDatasets = async () => {
            try {
                const response = await fetch('/api/database/roulette-series/datasets');
                if (!response.ok) {
                    return;
                }
                const payload = await response.json();
                const values = Array.isArray(payload?.datasets)
                    ? payload.datasets
                        .filter((entry: unknown) => typeof entry === 'object' && entry !== null)
                        .map((entry: { dataset_id?: unknown; dataset_name?: unknown }) => ({
                            dataset_id: parseDatasetId(entry.dataset_id),
                            dataset_name: typeof entry.dataset_name === 'string' ? entry.dataset_name : '',
                        }))
                        .filter((entry: DatasetOption) => entry.dataset_id.length > 0)
                    : [];
                setDatasets(values);
                if (values.length > 0 && !latestSetupRef.current.selectedDataset) {
                    onSetupChange({ selectedDataset: String(values[0].dataset_id), datasetSource: 'source' });
                }
            } catch (err) {
                console.error('Failed to load datasets:', err);
            }
        };

        loadCheckpoints();
        loadDatasets();
    }, [onSetupChange]);

    const updateBetAmount = async (value: number, forceSessionUpdate = false) => {
        onSetupChange({ betAmount: value });
        onSessionStateChange({ currentBet: value });
        if (!config || (!sessionActive && !forceSessionUpdate)) {
            return;
        }
        try {
            const response = await fetch(`/api/inference/sessions/${config.sessionId}/bet`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ bet_amount: value }),
            });
            if (!response.ok) {
                const payload = await response.json().catch(() => null);
                const detail = payload && typeof payload === 'object' && 'detail' in payload ? String(payload.detail) : 'Bet update failed.';
                throw new Error(detail);
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unable to update bet amount.';
            setError(message);
        }
    };

    const uploadDataset = async (file: File): Promise<{ dataset_id: number }> => {
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

    const clearInferenceContext = async () => {
        await fetch('/api/inference/context/clear', { method: 'POST' });
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            onSetupChange({
                datasetFileMetadata: {
                    name: file.name,
                    size: file.size,
                    type: file.type,
                },
            });
            setError(null);
            setIsUploading(true);
            try {
                const uploadPayload = await uploadDataset(file);
                const uploadedId = String(uploadPayload.dataset_id || '');
                if (!uploadedId) {
                    throw new Error('Upload completed but dataset_id was not returned.');
                }
                onSetupChange({
                    datasetSource: 'uploaded',
                    uploadedDatasetName: uploadedId,
                });
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Unable to upload dataset.';
                setError(message);
            } finally {
                setIsUploading(false);
            }
        }
    };

    const handleUploadClick = () => {
        if (fileInputRef.current) {
            fileInputRef.current.click();
        }
    };

    const handleClearUpload = async () => {
        onSetupChange({
            datasetSource: 'source',
            uploadedDatasetName: null,
            datasetFileMetadata: null,
        });
        await clearInferenceContext();
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const startSession = async (
        sessionId?: string,
        overrides?: { initialCapital?: number; betAmount?: number }
    ) => {
        if (!datasetId) {
            throw new Error('Select a dataset first.');
        }
        if (!setup.checkpoint) {
            throw new Error('Select a checkpoint first.');
        }
        const resolvedDatasetId = Number(datasetId);
        if (!Number.isInteger(resolvedDatasetId) || resolvedDatasetId <= 0) {
            throw new Error('Invalid dataset identifier.');
        }
        const gameCapital = overrides?.initialCapital ?? setup.initialCapital;
        const gameBet = overrides?.betAmount ?? setup.betAmount;
        const startPayload = {
            session_id: sessionId,
            checkpoint: setup.checkpoint,
            dataset_id: resolvedDatasetId,
            dataset_source: setup.datasetSource,
            game_capital: gameCapital,
            game_bet: gameBet,
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

        const payload = await response.json();
        const prediction = normalizePrediction(payload?.prediction);
        return { ...payload, prediction };
    };

    const handlePlay = async () => {
        if (setup.datasetSource === 'uploaded' && !setup.uploadedDatasetName) {
            setError('Upload the dataset before starting.');
            return;
        }
        if (setup.datasetSource !== 'uploaded' && !setup.selectedDataset) {
            setError('Select a dataset first.');
            return;
        }
        if (!setup.checkpoint) {
            setError('Select a checkpoint first.');
            return;
        }

        setIsStarting(true);
        setError(null);

        try {
            const session = await startSession();
            const prediction: PredictionResult = normalizePrediction(session.prediction);
            const currentCapital = Number(session.current_capital);
            const currentBet = prediction.currentBetAmount ?? Number(session.game_bet);

            const newConfig: GameConfig = {
                sessionId: String(session.session_id),
                checkpoint: String(session.checkpoint),
                datasetName: datasetId || '',
                initialCapital: Number(session.game_capital),
                betAmount: currentBet,
            };

            onGameConfigChange(newConfig);
            onSessionStateChange({
                isActive: true,
                currentCapital,
                currentBet: currentBet,
                lastPrediction: prediction,
                totalSteps: 0,
            });
            onHistoryChange([]);

            const initialStep: GameStep = {
                step: 1,
                predictedAction: prediction.action,
                predictedActionDesc: prediction.description,
                predictedConfidence: prediction.confidence,
                observed: null,
                observedInput: '',
                betAmount: currentBet,
                outcome: null,
                capitalAfter: currentCapital,
                isEditing: false,
            };
            onAddHistoryStep(initialStep);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unable to start session.';
            setError(message);
        } finally {
            setIsStarting(false);
        }
    };

    const handleStop = async () => {
        if (!config || !sessionActive) {
            return;
        }
        setIsStopping(true);
        setError(null);
        try {
            const response = await fetch(`/api/inference/sessions/${config.sessionId}/shutdown`, {
                method: 'POST',
            });
            if (!response.ok) {
                const payload = await response.json().catch(() => null);
                const detail = payload && typeof payload === 'object' && 'detail' in payload ? String(payload.detail) : 'Stop failed.';
                throw new Error(detail);
            }
            onSessionStateChange({ isActive: false });
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unable to stop session.';
            setError(message);
        } finally {
            setIsStopping(false);
        }
    };

    const clearPersistedSession = async () => {
        if (!config) {
            return;
        }
        await fetch(`/api/inference/sessions/${config.sessionId}/rows/clear`, {
            method: 'POST',
        });
    };

    const handleClear = async () => {
        if (sessionActive) {
            return;
        }
        await clearPersistedSession();
        onClearSession();
    };

    const requestNextPrediction = async (sessionId: string) => {
        const response = await fetch(`/api/inference/sessions/${sessionId}/next`, {
            method: 'POST',
        });

        if (!response.ok) {
            const payload = await response.json().catch(() => null);
            const detail = payload && typeof payload === 'object' && 'detail' in payload ? String(payload.detail) : 'Prediction failed.';
            throw new Error(detail);
        }

        const payload = await response.json();
        const prediction = normalizePrediction(payload?.prediction);
        return { ...payload, prediction };
    };

    const submitStep = async (sessionId: string, extraction: number) => {
        const response = await fetch(`/api/inference/sessions/${sessionId}/step`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ extraction }),
        });

        if (!response.ok) {
            const payload = await response.json().catch(() => null);
            const detail = payload && typeof payload === 'object' && 'detail' in payload ? String(payload.detail) : 'Step failed.';
            throw new Error(detail);
        }

        return await response.json();
    };

    const handleObservedChange = (index: number, value: string) => {
        const updated = history.map((row, rowIndex) =>
            rowIndex === index
                ? { ...row, observedInput: cleanObserved(value) }
                : row
        );
        onHistoryChange(updated);
    };

    const recomputeHistory = async (rows: GameStep[]) => {
        if (!config) {
            return;
        }
        setIsRecomputing(true);
        setError(null);

        try {
            await fetch(`/api/inference/sessions/${config.sessionId}/shutdown`, { method: 'POST' });
            await clearPersistedSession();

            const session = await startSession(config.sessionId, {
                initialCapital: config.initialCapital,
                betAmount: rows.length > 0 ? rows[0].betAmount : config.betAmount,
            });
            const prediction: PredictionResult = normalizePrediction(session.prediction);
            const currentCapital = Number(session.current_capital);
            const currentBet = prediction.currentBetAmount ?? Number(session.game_bet);
            const updatedHistory: GameStep[] = [];

            onGameConfigChange({
                sessionId: String(session.session_id),
                checkpoint: String(session.checkpoint),
                datasetName: datasetId || '',
                initialCapital: Number(session.game_capital),
                betAmount: currentBet,
            });

            onSessionStateChange({
                isActive: true,
                currentCapital,
                currentBet: currentBet,
                lastPrediction: prediction,
                totalSteps: 0,
            });

            updatedHistory.push({
                step: 1,
                predictedAction: prediction.action,
                predictedActionDesc: prediction.description,
                predictedConfidence: prediction.confidence,
                observed: null,
                observedInput: '',
                betAmount: currentBet,
                outcome: null,
                capitalAfter: currentCapital,
                isEditing: false,
            });

            let activeBet = currentBet;
            for (let index = 0; index < rows.length; index += 1) {
                const row = rows[index];
                if (row.observed === null) {
                    break;
                }
                if (row.betAmount !== activeBet) {
                    await updateBetAmount(row.betAmount, true);
                    activeBet = row.betAmount;
                }

                const result = await submitStep(String(session.session_id), row.observed);
                const capitalAfter = Number(result.capital_after);
                const outcome = Number(result.reward);
                const stepIndex = Number(result.step);

                const updatedRow = {
                    ...updatedHistory[updatedHistory.length - 1],
                    step: stepIndex,
                    observed: row.observed,
                    observedInput: String(row.observed),
                    outcome,
                    capitalAfter,
                    betAmount: row.betAmount,
                    isEditing: false,
                };
                updatedHistory[updatedHistory.length - 1] = updatedRow;

                onSessionStateChange({
                    currentCapital: capitalAfter,
                    totalSteps: stepIndex,
                });

                const hasNextRow = index < rows.length - 1;
                if (hasNextRow) {
                    const nextRowBet = rows[index + 1].betAmount;
                    if (nextRowBet !== activeBet) {
                        await updateBetAmount(nextRowBet, true);
                        activeBet = nextRowBet;
                    }
                    const nextPayload = await requestNextPrediction(String(session.session_id));
                    const nextPrediction: PredictionResult = normalizePrediction(nextPayload.prediction);
                    const nextBet = nextPrediction.currentBetAmount ?? nextRowBet;
                    updatedHistory.push({
                        step: stepIndex + 1,
                        predictedAction: nextPrediction.action,
                        predictedActionDesc: nextPrediction.description,
                        predictedConfidence: nextPrediction.confidence,
                        observed: null,
                        observedInput: '',
                        betAmount: nextBet,
                        outcome: null,
                        capitalAfter,
                        isEditing: false,
                    });
                    onSessionStateChange({
                        lastPrediction: nextPrediction,
                        currentBet: nextPrediction.currentBetAmount ?? activeBet,
                    });
                }
            }

            onHistoryChange(updatedHistory);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unable to recompute session.';
            setError(message);
        } finally {
            setIsRecomputing(false);
        }
    };

    const confirmObserved = async (index: number) => {
        if (!config || !sessionActive) {
            return;
        }
        const row = history[index];
        if (!row || row.observedInput === '') {
            return;
        }
        const extraction = parseInt(row.observedInput, 10);
        if (Number.isNaN(extraction)) {
            return;
        }
        setError(null);
        try {
            const result = await submitStep(config.sessionId, extraction);
            const capitalAfter = Number(result.capital_after);
            const outcome = Number(result.reward);
            const stepIndex = Number(result.step);

            const updated = history.map((item, rowIndex) =>
                rowIndex === index
                    ? {
                        ...item,
                        step: stepIndex,
                        observed: extraction,
                        observedInput: String(extraction),
                        outcome,
                        capitalAfter,
                        isEditing: false,
                    }
                    : item
            );

            onHistoryChange(updated);
            onSessionStateChange({
                currentCapital: capitalAfter,
                totalSteps: stepIndex,
            });
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unable to submit step.';
            setError(message);
        }
    };

    const handleModifyClick = async (index: number) => {
        const row = history[index];
        if (!row) {
            return;
        }
        if (row.observed === null) {
            await confirmObserved(index);
            return;
        }
        if (!row.isEditing) {
            const updated = history.map((item, rowIndex) =>
                rowIndex === index ? { ...item, isEditing: true } : item
            );
            onHistoryChange(updated);
            return;
        }
        const updatedRows = history.map((item, rowIndex) =>
            rowIndex === index
                ? {
                    ...item,
                    observed: item.observedInput === '' ? null : Number(item.observedInput),
                    isEditing: false,
                }
                : item
        );
        await recomputeHistory(updatedRows);
    };

    const handleRemove = async (index: number) => {
        if (index < 0 || index >= history.length) {
            return;
        }
        const updatedRows = history.filter((_, rowIndex) => rowIndex !== index);
        if (updatedRows.length === 0) {
            onHistoryChange([]);
            onSessionStateChange({ totalSteps: 0, currentCapital: setup.initialCapital });
            return;
        }
        await recomputeHistory(updatedRows);
    };

    const handleNextPrediction = async () => {
        if (!config || !sessionActive) {
            return;
        }
        setError(null);
        try {
            const nextPayload = await requestNextPrediction(config.sessionId);
            const prediction: PredictionResult = normalizePrediction(nextPayload.prediction);
            const nextStep = sessionState.totalSteps + 1;
            const activeBet = prediction.currentBetAmount ?? sessionState.currentBet;

            const newStep: GameStep = {
                step: nextStep,
                predictedAction: prediction.action,
                predictedActionDesc: prediction.description,
                predictedConfidence: prediction.confidence,
                observed: null,
                observedInput: '',
                betAmount: activeBet,
                outcome: null,
                capitalAfter: sessionState.currentCapital,
                isEditing: false,
            };

            onAddHistoryStep(newStep);
            onSessionStateChange({ lastPrediction: prediction, currentBet: activeBet });
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unable to get next prediction.';
            setError(message);
        }
    };

    const handleApplySuggestedBet = async () => {
        if (!sessionActive) {
            return;
        }
        const suggested = sessionState.lastPrediction?.suggestedBetAmount;
        if (suggested === undefined) {
            return;
        }
        await updateBetAmount(Number(suggested), true);
        if (sessionState.lastPrediction) {
            onSessionStateChange({
                lastPrediction: {
                    ...sessionState.lastPrediction,
                    currentBetAmount: Number(suggested),
                },
            });
        }
    };

    const canPlay = !sessionActive && !isStarting;
    const canStop = sessionActive && !isStopping;
    const canClear = !sessionActive && history.length > 0;

    return (
        <div className={styles.sessionContainer}>
            <div className={styles.leftPanel}>
                <div className={styles.card}>
                    <div className={styles.sectionTitle}>Select checkpoint</div>
                    <select
                        id="inference-checkpoint"
                        className={styles.select}
                        value={setup.checkpoint}
                        onChange={(e) => onSetupChange({ checkpoint: e.target.value })}
                        disabled={checkpoints.length === 0 || setupLocked}
                        aria-label="Model checkpoint"
                    >
                        {checkpoints.length === 0 ? (
                            <option value="">No checkpoints found</option>
                        ) : (
                            checkpoints.map((cp) => (
                                <option key={cp} value={cp}>{cp}</option>
                            ))
                        )}
                    </select>

                    <div className={styles.sectionTitle}>Selected dataset</div>
                    <div className={styles.datasetRow}>
                        <select
                            id="inference-dataset"
                            className={styles.select}
                            value={setup.datasetSource === 'uploaded'
                                ? setup.uploadedDatasetName || ''
                                : setup.selectedDataset}
                            onChange={(e) => onSetupChange({ selectedDataset: e.target.value, datasetSource: 'source' })}
                            disabled={datasets.length === 0 || datasetLocked}
                            aria-label="Inference dataset"
                        >
                            {setup.datasetSource === 'uploaded' && setup.uploadedDatasetName ? (
                                <option value={setup.uploadedDatasetName}>
                                    {setup.datasetFileMetadata?.name ?? setup.uploadedDatasetName}
                                </option>
                            ) : (
                                <>
                                    {datasets.length === 0 ? (
                                        <option value="">No datasets found</option>
                                    ) : (
                                        datasets.map((dataset) => (
                                            <option key={dataset.dataset_id} value={dataset.dataset_id}>
                                                {dataset.dataset_name}
                                            </option>
                                        ))
                                    )}
                                </>
                            )}
                        </select>
                        <input
                            type="file"
                            ref={fileInputRef}
                            accept=".csv,.xlsx"
                            onChange={handleFileChange}
                            className={styles.hiddenFileInput}
                            disabled={setupLocked}
                            aria-label="Upload inference dataset"
                        />
                        <button
                            type="button"
                            className={`${styles.secondaryButton} ${styles.uploadButton}`}
                            onClick={handleUploadClick}
                            disabled={setupLocked || isUploading}
                        >
                            {isUploading ? 'Uploading...' : 'Upload'}
                        </button>
                        <button
                            type="button"
                            className={styles.ghostButton}
                            onClick={handleClearUpload}
                            disabled={setupLocked || setup.datasetSource !== 'uploaded'}
                        >
                            Clear
                        </button>
                    </div>

                    <div className={styles.sectionTitle}>Initial parameters</div>
                    <div className={styles.inlineFields}>
                        <div className={styles.inlineField}>
                            <label className={styles.label} htmlFor="inference-initial-capital">Initial capital</label>
                            <input
                                id="inference-initial-capital"
                                type="number"
                                className={styles.input}
                                value={setup.initialCapital}
                                onChange={(e) => {
                                    const value = Number(e.target.value);
                                    onSetupChange({ initialCapital: value });
                                    if (!sessionState.isActive) {
                                        onSessionStateChange({ currentCapital: value });
                                    }
                                }}
                                min="1"
                                disabled={setupLocked}
                            />
                        </div>
                        <div className={styles.inlineField}>
                            <label className={styles.label} htmlFor="inference-bet-amount">Bet amount</label>
                            <input
                                id="inference-bet-amount"
                                type="number"
                                className={styles.input}
                                value={setup.betAmount}
                                onChange={(e) => updateBetAmount(Number(e.target.value))}
                                min="1"
                            />
                        </div>
                    </div>
                </div>

                <div className={styles.card}>
                    <div className={styles.statGrid}>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Current Capital</span>
                            <span className={`${styles.statValue} ${styles.statValueAccent}`}>
                                € {sessionState.currentCapital.toFixed(2)}
                            </span>
                        </div>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Profit/Loss</span>
                            {sessionState.totalSteps === 0 ? (
                                <span className={styles.statValue}>€ 0.00</span>
                            ) : (
                                <span className={`${styles.statValue} ${sessionState.currentCapital >= setup.initialCapital ? styles.outcomeWin : styles.outcomeLoss}`}>
                                    {(sessionState.currentCapital - setup.initialCapital) >= 0 ? '+' : ''}
                                    € {(sessionState.currentCapital - setup.initialCapital).toFixed(2)}
                                </span>
                            )}
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

                <div className={styles.predictionCard}>
                    <div className={styles.predictionTitle}>AI Suggestion</div>
                    <div className={styles.predictionValue}>
                        {sessionState.lastPrediction?.description || 'Waiting for a prediction'}
                    </div>
                    {sessionState.lastPrediction?.confidence !== undefined && (
                        <div className={styles.predictionDesc}>
                            Confidence: {(sessionState.lastPrediction.confidence * 100).toFixed(0)}%
                        </div>
                    )}
                    {sessionState.lastPrediction?.betStrategyName && (
                        <div className={styles.predictionDesc}>
                            Strategy: {sessionState.lastPrediction.betStrategyName}
                        </div>
                    )}
                    {sessionState.lastPrediction?.suggestedBetAmount !== undefined && (
                        <div className={styles.predictionDesc}>
                            Suggested Bet: € {sessionState.lastPrediction.suggestedBetAmount}
                        </div>
                    )}
                    <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={handleApplySuggestedBet}
                        disabled={
                            !sessionActive ||
                            sessionState.lastPrediction?.suggestedBetAmount === undefined
                        }
                    >
                        Apply Suggested Bet
                    </button>
                </div>
            </div>

            <div className={styles.rightPanel}>
                <div className={`${styles.card} ${styles.tableCard}`}>
                    <div className={styles.tableHeader}>
                        <h3 className={styles.tableTitle}>
                            <History size={16} /> Session History
                        </h3>
                        <div className={styles.headerActions}>
                            <button
                                type="button"
                                className={styles.primaryButton}
                                onClick={handlePlay}
                                disabled={!canPlay || isRecomputing}
                            >
                                <Play size={16} /> Play
                            </button>
                            <button
                                type="button"
                                className={styles.secondaryButton}
                                onClick={handleStop}
                                disabled={!canStop || isRecomputing}
                            >
                                <Square size={16} /> Stop
                            </button>
                            <button
                                type="button"
                                className={styles.ghostButton}
                                onClick={handleClear}
                                disabled={!canClear || isRecomputing}
                            >
                                Clear
                            </button>
                        </div>
                    </div>
                    {error && (
                        <div className={styles.errorText} role="alert" aria-live="polite">{error}</div>
                    )}
                    <div className={styles.tableBody}>
                        <table className={styles.historyTable}>
                            <thead>
                                <tr>
                                    <th>Step</th>
                                    <th>Prediction</th>
                                    <th>Observed</th>
                                    <th>Outcome</th>
                                    <th>Capital</th>
                                    <th className={styles.actionsHeader}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {history.map((step, index) => {
                                    const isLastRow = index === history.length - 1;
                                    const canNext =
                                        isLastRow &&
                                        step.observed !== null &&
                                        !step.isEditing &&
                                        sessionActive &&
                                        !isRecomputing;
                                    const canModify = sessionActive && !isRecomputing;

                                    return (
                                        <tr key={`${step.step}-${index}`}>
                                            <td>#{step.step}</td>
                                            <td>{step.predictedActionDesc}</td>
                                            <td>
                                                <input
                                                    type="text"
                                                    className={styles.tableInput}
                                                    value={step.observedInput}
                                                    aria-label={`Observed value for step ${step.step}`}
                                                    onChange={(e) => handleObservedChange(index, e.target.value)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') {
                                                            handleModifyClick(index);
                                                        }
                                                    }}
                                                    disabled={step.observed !== null && !step.isEditing}
                                                />
                                            </td>
                                            <td className={step.outcome !== null && step.outcome >= 0 ? styles.outcomeWin : styles.outcomeLoss}>
                                                {step.outcome === null ? '--' : `${step.outcome >= 0 ? '+' : ''}${step.outcome}`}
                                            </td>
                                            <td>{step.capitalAfter === null ? '--' : step.capitalAfter.toFixed(2)}</td>
                                            <td className={styles.actionsCell}>
                                                <div className={styles.actionsCellInner}>
                                                    <button
                                                        type="button"
                                                        className={styles.iconButton}
                                                        onClick={() => handleRemove(index)}
                                                        disabled={!canModify}
                                                        aria-label="Remove row"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        className={styles.iconButton}
                                                        onClick={() => handleModifyClick(index)}
                                                        disabled={!canModify}
                                                        aria-label={step.observed === null || step.isEditing ? 'Confirm observed' : 'Modify observed'}
                                                    >
                                                        {step.observed === null || step.isEditing ? <Check size={16} /> : <Pencil size={16} />}
                                                    </button>
                                                    <button
                                                        type="button"
                                                        className={styles.iconButton}
                                                        onClick={handleNextPrediction}
                                                        disabled={!canNext}
                                                        aria-label="Next prediction"
                                                    >
                                                        <Play size={16} />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                                {history.length === 0 && (
                                    <tr>
                                        <td colSpan={6} className={styles.emptyState}>
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
