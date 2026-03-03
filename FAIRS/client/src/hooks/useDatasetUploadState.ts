import { useCallback } from 'react';
import { useAppState } from '../context/AppStateContext';
import type { DatasetUploadState } from '../context/AppStateContext';
import type { DatasetUploadStateUpdates } from '../types/datasetUpload';

interface UseDatasetUploadStateResult {
    datasetUpload: DatasetUploadState;
    updateDatasetUploadState: (updates: DatasetUploadStateUpdates) => void;
    resetDatasetUploadState: () => void;
}

export const useDatasetUploadState = (): UseDatasetUploadStateResult => {
    const { state, dispatch } = useAppState();

    const updateDatasetUploadState = useCallback((updates: DatasetUploadStateUpdates) => {
        dispatch({ type: 'SET_DATASET_UPLOAD_STATE', payload: updates });
    }, [dispatch]);

    const resetDatasetUploadState = useCallback(() => {
        dispatch({ type: 'RESET_DATASET_UPLOAD' });
    }, [dispatch]);

    return {
        datasetUpload: state.training.datasetUpload,
        updateDatasetUploadState,
        resetDatasetUploadState,
    };
};
