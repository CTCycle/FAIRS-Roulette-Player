import { useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, RefObject } from 'react';
import {
    isSupportedDatasetFile,
    uploadDatasetFile,
} from '../utils/datasetUpload';
import type { DatasetUploadStateUpdates } from '../types/datasetUpload';

interface UseDatasetFileUploadOptions {
    onStateChange: (updates: DatasetUploadStateUpdates) => void;
    onReset: () => void;
    onUploadSuccess?: () => void;
}

interface UseDatasetFileUploadResult {
    selectedFile: File | null;
    fileInputRef: RefObject<HTMLInputElement | null>;
    handleFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
    handleDragOver: (event: DragEvent<HTMLElement>) => void;
    handleDrop: (event: DragEvent<HTMLElement>) => void;
    clearFiles: () => void;
    uploadDataset: () => Promise<void>;
}

const setUnsupportedFileMessage = (onStateChange: (updates: DatasetUploadStateUpdates) => void): void => {
    onStateChange({
        uploadStatus: 'error',
        uploadMessage: 'Unsupported file. Please upload a CSV or XLSX.',
    });
};

export const useDatasetFileUpload = ({
    onStateChange,
    onReset,
    onUploadSuccess,
}: UseDatasetFileUploadOptions): UseDatasetFileUploadResult => {
    // Keep actual File object in local ref (not serializable for context).
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const setSelectedDatasetFile = (file: File): void => {
        setSelectedFile(file);
        onStateChange({
            uploadStatus: 'idle',
            uploadMessage: '',
            files: [{ name: file.name, size: file.size, type: file.type }],
        });
    };

    const handleFileChange = (event: ChangeEvent<HTMLInputElement>): void => {
        const file = event.target.files?.[0] ?? null;
        if (!file) {
            return;
        }
        if (!isSupportedDatasetFile(file)) {
            setUnsupportedFileMessage(onStateChange);
            return;
        }
        setSelectedDatasetFile(file);
    };

    const handleDragOver = (event: DragEvent<HTMLElement>): void => {
        event.preventDefault();
        event.stopPropagation();
    };

    const handleDrop = (event: DragEvent<HTMLElement>): void => {
        event.preventDefault();
        event.stopPropagation();
        const file = event.dataTransfer.files?.[0] ?? null;
        if (!file) {
            return;
        }
        if (!isSupportedDatasetFile(file)) {
            setUnsupportedFileMessage(onStateChange);
            return;
        }
        setSelectedDatasetFile(file);
    };

    const clearFiles = (): void => {
        setSelectedFile(null);
        onReset();
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const uploadDataset = async (): Promise<void> => {
        if (!selectedFile) {
            onStateChange({
                uploadStatus: 'error',
                uploadMessage: 'Select a CSV/XLSX file first.',
            });
            return;
        }

        onStateChange({
            uploadStatus: 'uploading',
            uploadMessage: 'Uploading and importing dataset...',
        });

        try {
            const rows = await uploadDatasetFile(selectedFile);
            onStateChange({
                uploadStatus: 'success',
                uploadMessage: `Imported ${rows} rows into the database.`,
            });
            onUploadSuccess?.();
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Upload failed.';
            onStateChange({
                uploadStatus: 'error',
                uploadMessage: message,
            });
        }
    };

    return {
        selectedFile,
        fileInputRef,
        handleFileChange,
        handleDragOver,
        handleDrop,
        clearFiles,
        uploadDataset,
    };
};
