import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import type {
    GameStep,
    GameConfig,
    InferenceSessionSnapshot,
    InferenceSetupState,
    PredictionResult,
} from '../../types/inference';
import styles from './GameSession.module.css';
import { Check, History, Pencil, Play, Square, Trash2 } from 'lucide-react';
import { useInferenceSetupOptions } from '../../hooks/useInferenceSetupOptions';
import {
    clearInferenceContext,
    clearInferenceSessionRows,
    getInferenceSession,
    normalizePrediction,
    requestNextInferencePrediction,
    shutdownInferenceSession,
    startInferenceSession,
    submitInferenceStep,
    updateInferenceBet,
    uploadInferenceDataset,
} from '../../utils/inferenceApi';
import { ApiRequestError, isAbortError } from '../../utils/apiClient';
import {
    clearPersistedInferenceSession,
    loadPersistedInferenceSession,
    persistInferenceSession,
} from '../../utils/inferenceSessionStorage';
import { FeatureTip } from '../guidance/FeatureTip';
import { HelpPopover } from '../guidance/HelpPopover';

interface GameSessionProps {
    setup: InferenceSetupState;
    snapshot: InferenceSessionSnapshot;
    onSetupChange: (updates: Partial<InferenceSetupState>) => void;
    onSnapshotChange: (updates: Partial<InferenceSessionSnapshot>) => void;
}

const cleanObserved = (val: string) => {
    if (val === '') return '';
    const num = parseInt(val, 10);
    if (Number.isNaN(num)) return '';
    if (num < 0) return '0';
    if (num > 36) return '36';
    return String(num);
};

export const GameSession: React.FC<GameSessionProps> = ({
    setup,
    snapshot,
    onSetupChange,
    onSnapshotChange,
}) => {
    const {
        checkpoints,
        datasets,
        selectedCheckpointMetadata,
        selectedDatasetIsCompatible,
    } = useInferenceSetupOptions({
        setup,
        onSetupChange,
    });
    const [isUploading, setIsUploading] = useState(false);
    const [isStarting, setIsStarting] = useState(false);
    const [isStopping, setIsStopping] = useState(false);
    const [isRecomputing, setIsRecomputing] = useState(false);
    const [isMutating, setIsMutating] = useState(false);
    const [isRecovering, setIsRecovering] = useState(
        () => loadPersistedInferenceSession() !== null,
    );
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const mountedRef = useRef(true);
    const mutationInFlightRef = useRef(false);
    const mutationAbortRef = useRef<AbortController | null>(null);
    const recoveryRunRef = useRef(0);

    const {
        config,
        history,
        isActive: sessionActive,
        currentCapital,
        currentBet,
        lastPrediction,
        totalSteps,
    } = snapshot;
    const datasetLocked = sessionActive || setup.uploadedDatasetId !== null;
    const setupLocked = sessionActive;

    const datasetId = setup.uploadedDatasetId ?? setup.selectedDataset;

    const updateSnapshot = (updates: Partial<InferenceSessionSnapshot>): void => {
        onSnapshotChange(updates);
    };

    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
            mutationAbortRef.current?.abort();
        };
    }, []);

    const setLocalError = (message: string | null): void => {
        if (mountedRef.current) {
            setError(message);
        }
    };

    const resetExpiredSession = (): void => {
        clearPersistedInferenceSession();
        if (!mountedRef.current) {
            return;
        }
        updateSnapshot({
            config: null,
            isActive: false,
            currentCapital: setup.initialCapital,
            currentBet: setup.betAmount,
            lastPrediction: null,
            totalSteps: 0,
            history: [],
        });
    };

    const snapshotHistoryFromServer = (
        steps: Awaited<ReturnType<typeof getInferenceSession>>['steps'],
    ): GameStep[] => steps.map((step) => ({
        step: step.step,
        predictedAction: step.predicted_action,
        predictedActionDesc: step.predicted_action_desc,
        predictedRelativePreference: step.predicted_confidence ?? undefined,
        observed: step.observed_outcome_id,
        observedInput: step.observed_outcome_id === null
            ? ''
            : String(step.observed_outcome_id),
        betAmount: step.bet_amount,
        outcome: step.reward,
        capitalAfter: step.capital_after,
        isEditing: false,
    }));

    const applyServerSnapshot = (
        serverSnapshot: Awaited<ReturnType<typeof getInferenceSession>>,
        setupOverride: InferenceSetupState = setup,
    ): void => {
        const recoveredConfig: GameConfig = {
            sessionId: serverSnapshot.session_id,
            checkpoint: serverSnapshot.checkpoint,
            datasetId: serverSnapshot.dataset_id,
            initialCapital: serverSnapshot.initial_capital,
            betAmount: serverSnapshot.current_bet,
        };
        onSetupChange({
            checkpoint: serverSnapshot.checkpoint,
            selectedDataset: serverSnapshot.dataset_id,
            uploadedDatasetId: setupOverride.uploadedDatasetId === serverSnapshot.dataset_id
                ? setupOverride.uploadedDatasetId
                : null,
            initialCapital: serverSnapshot.initial_capital,
            betAmount: serverSnapshot.current_bet,
        });
        updateSnapshot({
            config: recoveredConfig,
            isActive: true,
            currentCapital: serverSnapshot.current_capital,
            currentBet: serverSnapshot.current_bet,
            lastPrediction: serverSnapshot.last_prediction,
            totalSteps: serverSnapshot.step_count,
            history: snapshotHistoryFromServer(serverSnapshot.steps),
        });
    };

    const reconcileSession = async (
        sessionId: string,
        signal?: AbortSignal,
    ): Promise<boolean> => {
        try {
            const serverSnapshot = await getInferenceSession(sessionId, signal);
            if (mountedRef.current) {
                applyServerSnapshot(serverSnapshot);
            }
            return true;
        } catch (err) {
            if (isAbortError(err)) {
                return false;
            }
            if (err instanceof ApiRequestError && err.status === 404) {
                resetExpiredSession();
                return false;
            }
            return false;
        }
    };

    const runMutation = async (
        operation: (signal: AbortSignal) => Promise<void>,
    ): Promise<void> => {
        if (mutationInFlightRef.current) {
            return;
        }
        mutationInFlightRef.current = true;
        const controller = new AbortController();
        mutationAbortRef.current = controller;
        if (mountedRef.current) {
            setIsMutating(true);
        }
        try {
            await operation(controller.signal);
        } finally {
            if (mutationAbortRef.current === controller) {
                mutationAbortRef.current = null;
            }
            mutationInFlightRef.current = false;
            if (mountedRef.current) {
                setIsMutating(false);
            }
        }
    };

    useEffect(() => {
        const persisted = loadPersistedInferenceSession();
        if (!persisted) {
            return;
        }
        const recoveryRun = recoveryRunRef.current + 1;
        recoveryRunRef.current = recoveryRun;
        const controller = new AbortController();
        const recover = async (): Promise<void> => {
            try {
                const serverSnapshot = await getInferenceSession(
                    persisted.config.sessionId,
                    controller.signal,
                );
                if (mountedRef.current) {
                    onSetupChange(persisted.setup);
                    applyServerSnapshot(serverSnapshot, persisted.setup);
                }
            } catch (err) {
                if (isAbortError(err)) {
                    return;
                }
                if (err instanceof ApiRequestError && err.status === 404) {
                    resetExpiredSession();
                    return;
                }
                setLocalError(err instanceof Error
                    ? `Unable to recover inference session: ${err.message}`
                    : 'Unable to recover inference session.');
            } finally {
                if (mountedRef.current && recoveryRunRef.current === recoveryRun) {
                    setIsRecovering(false);
                }
            }
        };
        void recover();
        return () => {
            controller.abort();
            if (recoveryRunRef.current === recoveryRun) {
                recoveryRunRef.current += 1;
            }
        };
        // Recovery is intentionally once per mounted page instance. The
        // referenced helpers are render-local but the persisted descriptor is
        // read only at mount.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (sessionActive && config) {
            persistInferenceSession(config, setup);
        }
    }, [config, sessionActive, setup]);

    const replaceHistory = (steps: GameStep[]): void => {
        updateSnapshot({ history: steps });
    };

    const addHistoryStep = (step: GameStep): void => {
        replaceHistory([...history, step]);
    };

    const applyBetAmount = async (
        value: number,
        forceSessionUpdate = false,
        sessionIdOverride?: string,
        signal?: AbortSignal,
        propagateError = false,
    ) => {
        if (!config || (!sessionActive && !forceSessionUpdate)) {
            if (mountedRef.current) {
                onSetupChange({ betAmount: value });
                updateSnapshot({ currentBet: value });
            }
            return;
        }
        try {
            await updateInferenceBet(sessionIdOverride ?? config.sessionId, value, signal);
            if (mountedRef.current) {
                onSetupChange({ betAmount: value });
                updateSnapshot({ currentBet: value });
            }
        } catch (err) {
            if (isAbortError(err)) {
                return;
            }
            if (err instanceof ApiRequestError && err.status === 404) {
                resetExpiredSession();
                return;
            }
            const message = err instanceof Error ? err.message : 'Unable to update bet amount.';
            setLocalError(message);
            if (propagateError) {
                throw err;
            }
        }
    };

    const updateBetAmount = async (value: number): Promise<void> => {
        await runMutation(async (signal) => {
            await applyBetAmount(value, false, undefined, signal);
        });
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            await runMutation(async (signal) => {
                onSetupChange({
                    datasetFileMetadata: {
                        name: file.name,
                        size: file.size,
                        type: file.type,
                    },
                });
                setLocalError(null);
                setIsUploading(true);
                try {
                    const uploadPayload = await uploadInferenceDataset(file, signal);
                    const uploadedId = uploadPayload.dataset_id;
                    if (uploadedId === null) {
                        throw new Error('Upload completed but dataset_id was not returned.');
                    }
                    if (mountedRef.current) {
                        onSetupChange({
                            uploadedDatasetId: uploadedId,
                        });
                    }
                } catch (err) {
                    if (!isAbortError(err)) {
                        const message = err instanceof Error ? err.message : 'Unable to upload dataset.';
                        setLocalError(message);
                    }
                } finally {
                    if (mountedRef.current) {
                        setIsUploading(false);
                    }
                }
            });
        }
    };

    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleClearUpload = async (): Promise<void> => {
        await runMutation(async (signal) => {
            try {
                await clearInferenceContext(signal);
                if (mountedRef.current) {
                    onSetupChange({
                        uploadedDatasetId: null,
                        datasetFileMetadata: null,
                    });
                    if (fileInputRef.current) fileInputRef.current.value = '';
                }
            } catch (err) {
                if (isAbortError(err)) {
                    return;
                }
                const message = err instanceof Error ? err.message : 'Unable to clear uploaded dataset.';
                setLocalError(message);
            }
        });
    };

    const startSession = async (
        overrides?: { initialCapital?: number; betAmount?: number },
        signal?: AbortSignal,
        preserveSessionId?: string,
    ) => {
        if (datasetId === null) {
            throw new Error('Select a dataset first.');
        }
        if (!setup.checkpoint) {
            throw new Error('Select a checkpoint first.');
        }
        const gameCapital = overrides?.initialCapital ?? setup.initialCapital;
        const gameBet = overrides?.betAmount ?? setup.betAmount;
        return startInferenceSession({
            checkpoint: setup.checkpoint,
            datasetId,
            gameCapital,
            gameBet,
            preserveSessionId,
        }, signal);
    };

    const handlePlay = async (): Promise<void> => {
        if (isRecovering) {
            return;
        }
        if (setup.uploadedDatasetId !== null && datasetId === null) {
            setLocalError('Upload the dataset before starting.');
            return;
        }
        if (setup.uploadedDatasetId === null && setup.selectedDataset === null) {
            setLocalError('Select a dataset first.');
            return;
        }
        if (!setup.checkpoint) {
            setLocalError('Select a checkpoint first.');
            return;
        }
        if (setup.uploadedDatasetId === null && !selectedDatasetIsCompatible) {
            const requiredRows = selectedCheckpointMetadata?.perceptiveFieldSize;
            if (requiredRows) {
                setLocalError(`Selected dataset needs at least ${requiredRows} rows for this checkpoint.`);
            } else {
                setLocalError('Selected dataset is not compatible with this checkpoint.');
            }
            return;
        }

        await runMutation(async (signal) => {
            if (mountedRef.current) {
                setIsStarting(true);
                setLocalError(null);
            }
            try {
                const session = await startSession(undefined, signal);
                const prediction: PredictionResult = normalizePrediction(session.prediction);
                const currentCapital = Number(session.current_capital);
                const currentBet = prediction.currentBetAmount ?? Number(session.game_bet);

                const newConfig: GameConfig = {
                    sessionId: String(session.session_id),
                    checkpoint: String(session.checkpoint),
                    datasetId: datasetId as number,
                    initialCapital: Number(session.game_capital),
                    betAmount: currentBet,
                };

                const initialStep: GameStep = {
                    step: 1,
                    predictedAction: prediction.action,
                    predictedActionDesc: prediction.description,
                    predictedRelativePreference: prediction.relativePreference,
                    observed: null,
                    observedInput: '',
                    betAmount: currentBet,
                    outcome: null,
                    capitalAfter: currentCapital,
                    isEditing: false,
                };
                if (mountedRef.current) {
                    updateSnapshot({
                        config: newConfig,
                        isActive: true,
                        currentCapital,
                        currentBet,
                        lastPrediction: prediction,
                        totalSteps: 0,
                        history: [initialStep],
                    });
                }
            } catch (err) {
                if (!isAbortError(err)) {
                    setLocalError(err instanceof Error ? err.message : 'Unable to start session.');
                }
            } finally {
                if (mountedRef.current) {
                    setIsStarting(false);
                }
            }
        });
    };

    const handleStop = async (): Promise<void> => {
        if (!config || !sessionActive) {
            return;
        }
        const sessionId = config.sessionId;
        await runMutation(async (signal) => {
            if (mountedRef.current) {
                setIsStopping(true);
                setLocalError(null);
            }
            try {
                await shutdownInferenceSession(sessionId, signal);
                clearPersistedInferenceSession();
                if (mountedRef.current) {
                    updateSnapshot({ isActive: false });
                }
            } catch (err) {
                if (isAbortError(err)) {
                    return;
                }
                if (err instanceof ApiRequestError && err.status === 404) {
                    resetExpiredSession();
                    return;
                }
                if (err instanceof ApiRequestError && err.status === 409) {
                    await reconcileSession(sessionId, signal);
                }
                setLocalError(err instanceof Error ? err.message : 'Unable to stop session.');
            } finally {
                if (mountedRef.current) {
                    setIsStopping(false);
                }
            }
        });
    };

    const clearPersistedSession = async (signal?: AbortSignal): Promise<void> => {
        if (!config) {
            return;
        }
        await clearInferenceSessionRows(config.sessionId, signal);
    };

    const handleClear = async (): Promise<void> => {
        if (sessionActive) {
            return;
        }
        await runMutation(async (signal) => {
            try {
                await clearPersistedSession(signal);
                clearPersistedInferenceSession();
                if (mountedRef.current) {
                    updateSnapshot({
                        config: null,
                        isActive: false,
                        currentCapital: setup.initialCapital,
                        currentBet: setup.betAmount,
                        lastPrediction: null,
                        totalSteps: 0,
                        history: [],
                    });
                }
            } catch (err) {
                if (isAbortError(err)) {
                    return;
                }
                if (err instanceof ApiRequestError && err.status === 404) {
                    resetExpiredSession();
                    return;
                }
                setLocalError(err instanceof Error ? err.message : 'Unable to clear session history.');
            }
        });
    };

    const handleObservedChange = (index: number, value: string) => {
        const updated = history.map((row, rowIndex) =>
            rowIndex === index
                ? { ...row, observedInput: cleanObserved(value) }
                : row
        );
        replaceHistory(updated);
    };

    const recomputeHistoryInternal = async (
        rows: GameStep[],
        signal: AbortSignal,
    ): Promise<void> => {
        if (!config) {
            return;
        }

        const previousConfig = config;
        let replacementSessionId: string | null = null;
        try {
            const session = await startSession({
                initialCapital: previousConfig.initialCapital,
                betAmount: rows.length > 0 ? rows[0].betAmount : previousConfig.betAmount,
            }, signal, previousConfig.sessionId);
            replacementSessionId = String(session.session_id);
            const prediction: PredictionResult = normalizePrediction(session.prediction);
            let lastReplayedPrediction = prediction;
            let currentCapital = Number(session.current_capital);
            let currentBet = prediction.currentBetAmount ?? Number(session.game_bet);
            const updatedHistory: GameStep[] = [{
                step: 1,
                predictedAction: prediction.action,
                predictedActionDesc: prediction.description,
                predictedRelativePreference: prediction.relativePreference,
                observed: null,
                observedInput: '',
                betAmount: currentBet,
                outcome: null,
                capitalAfter: currentCapital,
                isEditing: false,
            }];

            for (let index = 0; index < rows.length; index += 1) {
                const row = rows[index];
                if (row.observed === null) {
                    break;
                }
                if (row.betAmount !== currentBet) {
                    await updateInferenceBet(replacementSessionId, row.betAmount, signal);
                    currentBet = row.betAmount;
                }

                const result = await submitInferenceStep(
                    replacementSessionId,
                    row.observed,
                    signal,
                );
                currentCapital = Number(result.capital_after);
                const outcome = Number(result.reward);
                const stepIndex = Number(result.step);
                updatedHistory[updatedHistory.length - 1] = {
                    ...updatedHistory[updatedHistory.length - 1],
                    step: stepIndex,
                    observed: row.observed,
                    observedInput: String(row.observed),
                    outcome,
                    capitalAfter: currentCapital,
                    betAmount: row.betAmount,
                    isEditing: false,
                };

                const hasNextRow = index < rows.length - 1;
                if (hasNextRow) {
                    const nextRowBet = rows[index + 1].betAmount;
                    if (nextRowBet !== currentBet) {
                        await updateInferenceBet(replacementSessionId, nextRowBet, signal);
                        currentBet = nextRowBet;
                    }
                    const nextPayload = await requestNextInferencePrediction(
                        replacementSessionId,
                        signal,
                    );
                    const nextPrediction: PredictionResult = normalizePrediction(nextPayload.prediction);
                    lastReplayedPrediction = nextPrediction;
                    currentBet = nextPrediction.currentBetAmount ?? currentBet;
                    updatedHistory.push({
                        step: stepIndex + 1,
                        predictedAction: nextPrediction.action,
                        predictedActionDesc: nextPrediction.description,
                        predictedRelativePreference: nextPrediction.relativePreference,
                        observed: null,
                        observedInput: '',
                        betAmount: currentBet,
                        outcome: null,
                        capitalAfter: currentCapital,
                        isEditing: false,
                    });
                }
            }

            // The old live session remains usable until the replacement has been
            // completely started and replayed. Commit the switch only afterward.
            await shutdownInferenceSession(previousConfig.sessionId, signal);
            const newConfig: GameConfig = {
                sessionId: replacementSessionId,
                checkpoint: String(session.checkpoint),
                datasetId: Number(datasetId),
                initialCapital: Number(session.game_capital),
                betAmount: currentBet,
            };
            if (mountedRef.current) {
                onSetupChange({
                    checkpoint: newConfig.checkpoint,
                    selectedDataset: newConfig.datasetId,
                    initialCapital: newConfig.initialCapital,
                    betAmount: currentBet,
                });
                updateSnapshot({
                    config: newConfig,
                    isActive: true,
                    currentCapital,
                    currentBet,
                    lastPrediction: lastReplayedPrediction,
                    totalSteps: updatedHistory.filter((step) => step.observed !== null).length,
                    history: updatedHistory,
                });
            }
            replacementSessionId = null;
        } catch (err) {
            if (replacementSessionId !== null) {
                try {
                    // Cleanup is independent of the UI request signal: aborting a
                    // request during navigation must not orphan the replacement.
                    await shutdownInferenceSession(replacementSessionId);
                } catch (cleanupError) {
                    console.error('Failed to clean up replacement inference session:', cleanupError);
                }
            }
            throw err;
        }
    };

    const recomputeHistory = async (rows: GameStep[]): Promise<void> => {
        await runMutation(async (signal) => {
            if (mountedRef.current) {
                setIsRecomputing(true);
                setLocalError(null);
            }
            try {
                await recomputeHistoryInternal(rows, signal);
            } catch (err) {
                if (isAbortError(err)) {
                    return;
                }
                if (err instanceof ApiRequestError && err.status === 404) {
                    resetExpiredSession();
                    return;
                }
                if (err instanceof ApiRequestError && err.status === 409 && config) {
                    await reconcileSession(config.sessionId, signal);
                }
                setLocalError(err instanceof Error ? err.message : 'Unable to recompute session.');
            } finally {
                if (mountedRef.current) {
                    setIsRecomputing(false);
                }
            }
        });
    };

    const confirmObservedInternal = async (
        index: number,
        signal: AbortSignal,
    ): Promise<void> => {
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
        const result = await submitInferenceStep(config.sessionId, extraction, signal);
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

        replaceHistory(updated);
        updateSnapshot({
            currentCapital: capitalAfter,
            totalSteps: stepIndex,
        });
    };

    const confirmObserved = async (index: number): Promise<void> => {
        await runMutation(async (signal) => {
            setLocalError(null);
            try {
                await confirmObservedInternal(index, signal);
            } catch (err) {
                if (isAbortError(err)) {
                    return;
                }
                if (err instanceof ApiRequestError && err.status === 404) {
                    resetExpiredSession();
                    return;
                }
                if (err instanceof ApiRequestError && err.status === 409 && config) {
                    await reconcileSession(config.sessionId, signal);
                }
                setLocalError(err instanceof Error ? err.message : 'Unable to submit step.');
            }
        });
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
            replaceHistory(updated);
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

    const handleRemove = async (index: number): Promise<void> => {
        if (index < 0 || index >= history.length) {
            return;
        }
        const updatedRows = history.filter((_, rowIndex) => rowIndex !== index);
        if (updatedRows.length === 0) {
            await recomputeHistory([]);
            return;
        }
        await recomputeHistory(updatedRows);
    };

    const handleNextPrediction = async (): Promise<void> => {
        if (!config || !sessionActive) {
            return;
        }
        await runMutation(async (signal) => {
            setLocalError(null);
            try {
                const nextPayload = await requestNextInferencePrediction(config.sessionId, signal);
                const prediction: PredictionResult = normalizePrediction(nextPayload.prediction);
                const nextStep = totalSteps + 1;
                const activeBet = prediction.currentBetAmount ?? currentBet;

                const newStep: GameStep = {
                    step: nextStep,
                    predictedAction: prediction.action,
                    predictedActionDesc: prediction.description,
                        predictedRelativePreference: prediction.relativePreference,
                    observed: null,
                    observedInput: '',
                    betAmount: activeBet,
                    outcome: null,
                    capitalAfter: currentCapital,
                    isEditing: false,
                };

                addHistoryStep(newStep);
                updateSnapshot({
                    lastPrediction: prediction,
                    currentBet: activeBet,
                    config: { ...config, betAmount: activeBet },
                });
            } catch (err) {
                if (isAbortError(err)) {
                    return;
                }
                if (err instanceof ApiRequestError && err.status === 404) {
                    resetExpiredSession();
                    return;
                }
                if (err instanceof ApiRequestError && err.status === 409) {
                    await reconcileSession(config.sessionId, signal);
                }
                setLocalError(err instanceof Error ? err.message : 'Unable to get next prediction.');
            }
        });
    };

    const handleApplySuggestedBet = async (): Promise<void> => {
        if (!sessionActive) {
            return;
        }
        const suggested = lastPrediction?.suggestedBetAmount;
        if (suggested === undefined) {
            return;
        }
        try {
            await runMutation(async (signal) => {
                await applyBetAmount(Number(suggested), true, undefined, signal, true);
                if (mountedRef.current && lastPrediction) {
                    updateSnapshot({
                        config: config ? { ...config, betAmount: Number(suggested) } : config,
                        lastPrediction: {
                            ...lastPrediction,
                            currentBetAmount: Number(suggested),
                        },
                    });
                }
            });
        } catch (err) {
            if (!isAbortError(err)) {
                setLocalError(err instanceof Error ? err.message : 'Unable to update bet amount.');
            }
        }
    };

    const canPlay = !sessionActive && !isStarting && !isMutating && !isRecovering;
    const canStop = sessionActive && !isStopping && !isMutating && !isRecovering;
    const canClear = !sessionActive && history.length > 0 && !isMutating && !isRecovering;

    return (
        <div className={styles.sessionContainer}>
            <div className={styles.leftPanel}>
                <div className={styles.card} data-guidance-target="inference-setup">
                    <div className={styles.sectionTitle}>Select checkpoint</div>
                    <select
                        id="inference-checkpoint"
                        className={styles.select}
                        value={setup.checkpoint}
                        onChange={(e) => onSetupChange({ checkpoint: e.target.value })}
                        disabled={checkpoints.length === 0 || setupLocked || isMutating || isRecovering}
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

                    {checkpoints.length === 0 && (
                        <FeatureTip
                            id="inference-no-checkpoint"
                            title="Train a checkpoint first"
                            action={<Link to="/training">Open Training</Link>}
                        >
                            Inference needs a trained checkpoint. Train one first, then return here with a compatible dataset.
                        </FeatureTip>
                    )}

                    <div className={styles.sectionTitle}>Selected dataset</div>
                    <div className={styles.datasetRow}>
                        <select
                            id="inference-dataset"
                            className={styles.select}
                            value={setup.uploadedDatasetId ?? setup.selectedDataset ?? ''}
                            onChange={(e) => onSetupChange({ selectedDataset: Number(e.target.value) })}
                            disabled={datasets.length === 0 || datasetLocked || isMutating || isRecovering}
                            aria-label="Inference dataset"
                        >
                            {setup.uploadedDatasetId !== null ? (
                                <option value={setup.uploadedDatasetId}>
                                    {setup.datasetFileMetadata?.name ?? `Dataset ${setup.uploadedDatasetId}`}
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
                            disabled={setupLocked || isMutating || isRecovering}
                            aria-label="Upload inference dataset"
                        />
                        <button
                            type="button"
                            className={`${styles.secondaryButton} ${styles.uploadButton} ${styles.compactButton}`}
                            onClick={handleUploadClick}
                            disabled={setupLocked || isUploading || isMutating || isRecovering}
                        >
                            {isUploading ? 'Uploading...' : 'Upload'}
                        </button>
                        <button
                            type="button"
                            className={`${styles.ghostButton} ${styles.compactButton}`}
                            onClick={handleClearUpload}
                            disabled={setupLocked || setup.uploadedDatasetId === null || isMutating || isRecovering}
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
                                    if (!sessionActive) {
                                        updateSnapshot({ currentCapital: value });
                                    }
                                }}
                                min="1"
                                disabled={setupLocked || isMutating || isRecovering}
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
                                disabled={isMutating || isRecovering}
                            />
                        </div>
                    </div>
                </div>

                <div className={styles.card}>
                    <div className={styles.statGrid}>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Current Capital</span>
                            <span className={`${styles.statValue} ${styles.statValueAccent}`}>
                                € {currentCapital.toFixed(2)}
                            </span>
                        </div>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Profit/Loss</span>
                            {totalSteps === 0 ? (
                                <span className={styles.statValue}>€ 0.00</span>
                            ) : (
                                <span className={`${styles.statValue} ${currentCapital >= setup.initialCapital ? styles.outcomeWin : styles.outcomeLoss}`}>
                                    {(currentCapital - setup.initialCapital) >= 0 ? '+' : ''}
                                    € {(currentCapital - setup.initialCapital).toFixed(2)}
                                </span>
                            )}
                        </div>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Bet Amount</span>
                            <span className={styles.statValue}>€ {currentBet}</span>
                        </div>
                        <div className={styles.statItem}>
                            <span className={styles.statLabel}>Steps</span>
                            <span className={styles.statValue}>{totalSteps}</span>
                        </div>
                    </div>
                </div>

                <div className={styles.predictionCard}>
                    <div className={styles.predictionTitle}>
                        <span>AI Suggestion</span>
                        <HelpPopover title="How the suggestion works">
                            Play starts a session and fetches a prediction. Apply Suggested Bet only changes the current bet amount; it does not advance the session.
                        </HelpPopover>
                    </div>
                    <div className={styles.predictionValue}>
                        {lastPrediction?.description || 'Waiting for a prediction'}
                    </div>
                    {lastPrediction?.betStrategyName && (
                        <div className={styles.predictionDesc}>
                            Strategy: {lastPrediction.betStrategyName}
                        </div>
                    )}
                    {lastPrediction?.suggestedBetAmount !== undefined && (
                        <div className={styles.predictionDesc}>
                            Suggested Bet: € {lastPrediction.suggestedBetAmount}
                        </div>
                    )}
                    <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={handleApplySuggestedBet}
                        disabled={
                            !sessionActive ||
                            isRecovering ||
                            lastPrediction?.suggestedBetAmount === undefined
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
                                className={`${styles.primaryButton} ${styles.compactButton}`}
                                onClick={handlePlay}
                                disabled={!canPlay || isRecomputing}
                                data-guidance-target="inference-play"
                            >
                                <Play size={16} /> Play
                            </button>
                            <button
                                type="button"
                                className={`${styles.secondaryButton} ${styles.compactButton}`}
                                onClick={handleStop}
                                disabled={!canStop || isRecomputing}
                            >
                                <Square size={16} /> Stop
                            </button>
                            <button
                                type="button"
                                className={`${styles.ghostButton} ${styles.compactButton}`}
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
                    {history.length === 0 && (
                        <FeatureTip id="inference-session-empty" title="One round at a time">
                            Start with Play. After each prediction, enter the observed wheel value and confirm it before requesting the next round.
                        </FeatureTip>
                    )}
                    <div className={styles.tableBody} data-guidance-target="inference-observation">
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
                                {history.length === 0 ? (
                                    Array.from({ length: 3 }, (_, index) => (
                                        <tr
                                            key={`placeholder-${index}`}
                                            className={styles.placeholderRow}
                                            aria-hidden="true"
                                        >
                                            <td>—</td>
                                            <td>—</td>
                                            <td>—</td>
                                            <td>—</td>
                                            <td>—</td>
                                            <td className={styles.actionsCell}>—</td>
                                        </tr>
                                    ))
                                ) : (
                                    history.map((step, index) => {
                                        const isLastRow = index === history.length - 1;
                                        const canNext =
                                            isLastRow &&
                                            step.observed !== null &&
                                            !step.isEditing &&
                                            sessionActive &&
                                            !isRecomputing &&
                                            !isMutating;
                                        const canModify = sessionActive && !isRecomputing && !isMutating;

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
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};

