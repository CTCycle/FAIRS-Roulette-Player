import type {
    GameConfig,
    InferenceSetupState,
} from '../types/inference';

const STORAGE_KEY = 'fairs.roulette.inference-session.v1';
const STORAGE_VERSION = 1;

export interface PersistedInferenceSession {
    version: typeof STORAGE_VERSION;
    config: GameConfig;
    setup: InferenceSetupState;
}

const isRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null && !Array.isArray(value)
);

const isFiniteNumber = (value: unknown): value is number => (
    typeof value === 'number' && Number.isFinite(value)
);

const isValidConfig = (value: unknown): value is GameConfig => {
    if (!isRecord(value)) {
        return false;
    }
    const datasetId = value.datasetId;
    const initialCapital = value.initialCapital;
    const betAmount = value.betAmount;
    return typeof value.sessionId === 'string'
        && value.sessionId.length > 0
        && typeof value.checkpoint === 'string'
        && value.checkpoint.length > 0
        && typeof datasetId === 'number'
        && Number.isInteger(datasetId)
        && datasetId > 0
        && typeof initialCapital === 'number'
        && Number.isInteger(initialCapital)
        && initialCapital > 0
        && typeof betAmount === 'number'
        && Number.isInteger(betAmount)
        && betAmount > 0;
};

const isValidSetup = (value: unknown): value is InferenceSetupState => {
    if (!isRecord(value)) {
        return false;
    }
    return isFiniteNumber(value.initialCapital)
        && value.initialCapital > 0
        && isFiniteNumber(value.betAmount)
        && value.betAmount > 0
        && typeof value.checkpoint === 'string'
        && (value.selectedDataset === null || Number.isInteger(value.selectedDataset))
        && (value.uploadedDatasetId === null || Number.isInteger(value.uploadedDatasetId))
        && (value.datasetFileMetadata === null || isRecord(value.datasetFileMetadata));
};

export const loadPersistedInferenceSession = (): PersistedInferenceSession | null => {
    if (typeof window === 'undefined') {
        return null;
    }
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) {
            return null;
        }
        const value: unknown = JSON.parse(raw);
        if (!isRecord(value)
            || value.version !== STORAGE_VERSION
            || !isValidConfig(value.config)
            || !isValidSetup(value.setup)) {
            window.localStorage.removeItem(STORAGE_KEY);
            return null;
        }
        return {
            version: STORAGE_VERSION,
            config: value.config,
            setup: value.setup,
        };
    } catch {
        return null;
    }
};

export const persistInferenceSession = (
    config: GameConfig,
    setup: InferenceSetupState,
): void => {
    if (typeof window === 'undefined') {
        return;
    }
    try {
        const value: PersistedInferenceSession = {
            version: STORAGE_VERSION,
            config,
            setup,
        };
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    } catch {
        // Storage is advisory. A quota or privacy-mode failure must not stop play.
    }
};

export const clearPersistedInferenceSession = (): void => {
    if (typeof window === 'undefined') {
        return;
    }
    try {
        window.localStorage.removeItem(STORAGE_KEY);
    } catch {
        // Ignore storage cleanup failures; the server remains authoritative.
    }
};
