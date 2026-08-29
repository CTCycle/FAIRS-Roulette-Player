import { useCallback, useState } from 'react';
import type {
    DatasetUploadState,
    DatasetUploadStateUpdates,
} from '../types/datasetUpload';

const initialDatasetUploadState: DatasetUploadState = {
    files: [],
    uploadStatus: 'idle',
    uploadMessage: '',
};

interface UseDatasetUploadStateResult {
    datasetUpload: DatasetUploadState;
    updateDatasetUploadState: (updates: DatasetUploadStateUpdates) => void;
    resetDatasetUploadState: () => void;
}

export const useDatasetUploadState = (): UseDatasetUploadStateResult => {
    const [datasetUpload, setDatasetUpload] = useState(initialDatasetUploadState);

    const updateDatasetUploadState = useCallback((updates: DatasetUploadStateUpdates) => {
        setDatasetUpload((current) => ({ ...current, ...updates }));
    }, []);

    const resetDatasetUploadState = useCallback(() => {
        setDatasetUpload(initialDatasetUploadState);
    }, []);

    return {
        datasetUpload,
        updateDatasetUploadState,
        resetDatasetUploadState,
    };
};
