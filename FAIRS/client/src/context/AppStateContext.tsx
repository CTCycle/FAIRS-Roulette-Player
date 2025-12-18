import React, { createContext, useContext, useReducer, type ReactNode } from 'react';
import type { GameConfig, SessionState, GameStep } from '../types/inference';

// ============================================================================
// State Interfaces
// ============================================================================

export interface FileMetadata {
    name: string;
    size: number;
    type: string;
}

export interface DatabaseState {
    selectedTable: string;
    tableData: {
        columns: string[];
        rows: Record<string, unknown>[];
        offset: number;
        limit: number;
    } | null;
    tableStats: {
        table_name: string;
        verbose_name: string;
        row_count: number;
        column_count: number;
    } | null;
}

export interface DatasetUploadState {
    files: FileMetadata[];
    uploadStatus: 'idle' | 'uploading' | 'success' | 'error';
    uploadMessage: string;
}

export interface TrainingNewConfig {
    perceptiveField: number;
    numNeurons: number;
    embeddingDims: number;
    explorationRate: number;
    explorationRateDecay: number;
    minExplorationRate: number;
    discountRate: number;
    modelUpdateFreq: number;
    betAmount: number;
    initialCapital: number;
    useDataGen: boolean;
    numGeneratedSamples: number;
    trainSampleSize: number;
    validationSize: number;
    splitSeed: number;
    setShuffle: boolean;
    shuffleSize: number;
    episodes: number;
    maxStepsEpisode: number;
    batchSize: number;
    learningRate: number;
    trainingSeed: number;
    deviceGPU: boolean;
    deviceID: number;
    maxMemorySize: number;
    replayBufferSize: number;
    saveCheckpoints: boolean;
    checkpointsFreq: number;
    useTensorboard: boolean;
    numWorkers: number;
}

export interface TrainingResumeConfig {
    numAdditionalEpisodes: number;
}

export interface TrainingState {
    isTraining: boolean;
    datasetUpload: DatasetUploadState;
    newConfig: TrainingNewConfig;
    resumeConfig: TrainingResumeConfig;
}

export interface InferenceSetupState {
    initialCapital: number;
    betAmount: number;
    checkpoint: string;
    datasetFileMetadata: FileMetadata | null;
}

export interface InferenceState {
    gameConfig: GameConfig | null;
    setup: InferenceSetupState;
    sessionState: SessionState;
    history: GameStep[];
}

export interface AppState {
    database: DatabaseState;
    training: TrainingState;
    inference: InferenceState;
}

// ============================================================================
// Initial State
// ============================================================================

const initialDatabaseState: DatabaseState = {
    selectedTable: '',
    tableData: null,
    tableStats: null,
};

const initialDatasetUploadState: DatasetUploadState = {
    files: [],
    uploadStatus: 'idle',
    uploadMessage: '',
};

const initialNewConfig: TrainingNewConfig = {
    perceptiveField: 64,
    numNeurons: 64,
    embeddingDims: 200,
    explorationRate: 0.75,
    explorationRateDecay: 0.995,
    minExplorationRate: 0.10,
    discountRate: 0.50,
    modelUpdateFreq: 10,
    betAmount: 10,
    initialCapital: 1000,
    useDataGen: false,
    numGeneratedSamples: 10000,
    trainSampleSize: 1.0,
    validationSize: 0.20,
    splitSeed: 42,
    setShuffle: true,
    shuffleSize: 256,
    episodes: 10,
    maxStepsEpisode: 2000,
    batchSize: 32,
    learningRate: 0.0001,
    trainingSeed: 42,
    deviceGPU: false,
    deviceID: 0,
    maxMemorySize: 10000,
    replayBufferSize: 1000,
    saveCheckpoints: false,
    checkpointsFreq: 1,
    useTensorboard: false,
    numWorkers: 4,
};

const initialResumeConfig: TrainingResumeConfig = {
    numAdditionalEpisodes: 10,
};

const initialTrainingState: TrainingState = {
    isTraining: false,
    datasetUpload: initialDatasetUploadState,
    newConfig: initialNewConfig,
    resumeConfig: initialResumeConfig,
};

const initialInferenceSetupState: InferenceSetupState = {
    initialCapital: 100,
    betAmount: 1,
    checkpoint: '',
    datasetFileMetadata: null,
};

const initialSessionState: SessionState = {
    isActive: false,
    currentCapital: 0,
    currentBet: 0,
    history: [],
    lastPrediction: null,
    totalSteps: 0,
};

const initialInferenceState: InferenceState = {
    gameConfig: null,
    setup: initialInferenceSetupState,
    sessionState: initialSessionState,
    history: [],
};

const initialAppState: AppState = {
    database: initialDatabaseState,
    training: initialTrainingState,
    inference: initialInferenceState,
};

// ============================================================================
// Actions
// ============================================================================

type AppAction =
    // Database Actions
    | { type: 'SET_DATABASE_SELECTED_TABLE'; payload: string }
    | { type: 'SET_DATABASE_TABLE_DATA'; payload: DatabaseState['tableData'] }
    | { type: 'SET_DATABASE_TABLE_STATS'; payload: DatabaseState['tableStats'] }
    // Training Actions
    | { type: 'SET_TRAINING_IS_TRAINING'; payload: boolean }
    | { type: 'SET_DATASET_UPLOAD_STATE'; payload: Partial<DatasetUploadState> }
    | { type: 'SET_TRAINING_NEW_CONFIG'; payload: Partial<TrainingNewConfig> }
    | { type: 'SET_TRAINING_RESUME_CONFIG'; payload: Partial<TrainingResumeConfig> }
    | { type: 'RESET_DATASET_UPLOAD' }
    // Inference Actions
    | { type: 'SET_INFERENCE_GAME_CONFIG'; payload: GameConfig | null }
    | { type: 'SET_INFERENCE_SETUP'; payload: Partial<InferenceSetupState> }
    | { type: 'SET_INFERENCE_SESSION_STATE'; payload: Partial<SessionState> }
    | { type: 'ADD_INFERENCE_HISTORY_STEP'; payload: GameStep }
    | { type: 'RESET_INFERENCE_SESSION' };

// ============================================================================
// Reducer
// ============================================================================

function appReducer(state: AppState, action: AppAction): AppState {
    switch (action.type) {
        // Database
        case 'SET_DATABASE_SELECTED_TABLE':
            return {
                ...state,
                database: { ...state.database, selectedTable: action.payload },
            };
        case 'SET_DATABASE_TABLE_DATA':
            return {
                ...state,
                database: { ...state.database, tableData: action.payload },
            };
        case 'SET_DATABASE_TABLE_STATS':
            return {
                ...state,
                database: { ...state.database, tableStats: action.payload },
            };

        // Training
        case 'SET_TRAINING_IS_TRAINING':
            return {
                ...state,
                training: { ...state.training, isTraining: action.payload },
            };
        case 'SET_DATASET_UPLOAD_STATE':
            return {
                ...state,
                training: {
                    ...state.training,
                    datasetUpload: { ...state.training.datasetUpload, ...action.payload },
                },
            };
        case 'SET_TRAINING_NEW_CONFIG':
            return {
                ...state,
                training: {
                    ...state.training,
                    newConfig: { ...state.training.newConfig, ...action.payload },
                },
            };
        case 'SET_TRAINING_RESUME_CONFIG':
            return {
                ...state,
                training: {
                    ...state.training,
                    resumeConfig: { ...state.training.resumeConfig, ...action.payload },
                },
            };
        case 'RESET_DATASET_UPLOAD':
            return {
                ...state,
                training: {
                    ...state.training,
                    datasetUpload: initialDatasetUploadState,
                },
            };

        // Inference
        case 'SET_INFERENCE_GAME_CONFIG':
            return {
                ...state,
                inference: { ...state.inference, gameConfig: action.payload },
            };
        case 'SET_INFERENCE_SETUP':
            return {
                ...state,
                inference: {
                    ...state.inference,
                    setup: { ...state.inference.setup, ...action.payload },
                },
            };
        case 'SET_INFERENCE_SESSION_STATE':
            return {
                ...state,
                inference: {
                    ...state.inference,
                    sessionState: { ...state.inference.sessionState, ...action.payload },
                },
            };
        case 'ADD_INFERENCE_HISTORY_STEP':
            return {
                ...state,
                inference: {
                    ...state.inference,
                    history: [...state.inference.history, action.payload],
                },
            };
        case 'RESET_INFERENCE_SESSION':
            return {
                ...state,
                inference: {
                    ...state.inference,
                    gameConfig: null,
                    sessionState: initialSessionState,
                    history: [],
                },
            };

        default:
            return state;
    }
}

// ============================================================================
// Context
// ============================================================================

interface AppStateContextType {
    state: AppState;
    dispatch: React.Dispatch<AppAction>;
}

const AppStateContext = createContext<AppStateContextType | undefined>(undefined);

export const AppStateProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [state, dispatch] = useReducer(appReducer, initialAppState);

    return (
        <AppStateContext.Provider value={{ state, dispatch }}>
            {children}
        </AppStateContext.Provider>
    );
};

export const useAppState = (): AppStateContextType => {
    const context = useContext(AppStateContext);
    if (context === undefined) {
        throw new Error('useAppState must be used within an AppStateProvider');
    }
    return context;
};

// Export action type for components
export type { AppAction };
