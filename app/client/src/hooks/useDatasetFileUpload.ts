import { useEffect, useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, RefObject } from 'react';
import {
    isSupportedDatasetFile,
    uploadDatasetFile,
} from '../utils/datasetUpload';
import type { DatasetUploadStateUpdates } from '../types/datasetUpload';
import { isAbortError } from '../utils/apiClient';

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
    // Keep the actual File object local; only display metadata leaves this hook.
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const uploadAbortRef = useRef<AbortController | null>(null);
    const uploadInFlightRef = useRef(false);
    const mountedRef = useRef(true);

    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
            uploadAbortRef.current?.abort();
        };
    }, []);

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
        uploadAbortRef.current?.abort();
        setSelectedFile(null);
        onReset();
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const uploadDataset = async (): Promise<void> => {
        if (!selectedFile || uploadInFlightRef.current) {
            if (!selectedFile) {
                onStateChange({
                    uploadStatus: 'error',
                    uploadMessage: 'Select a CSV/XLSX file first.',
                });
            }
            return;
        }
        if (!mountedRef.current) {
            return;
        }

        uploadInFlightRef.current = true;
        const controller = new AbortController();
        uploadAbortRef.current = controller;
        onStateChange({
            uploadStatus: 'uploading',
            uploadMessage: 'Uploading and importing dataset...',
        });

        try {
            const rows = await uploadDatasetFile(selectedFile, controller.signal);
            if (!mountedRef.current) {
                return;
            }
            onStateChange({
                uploadStatus: 'success',
                uploadMessage: `Imported ${rows} rows into the database.`,
            });
            onUploadSuccess?.();
        } catch (error) {
            if (isAbortError(error) || !mountedRef.current) {
                return;
            }
            const message = error instanceof Error ? error.message : 'Upload failed.';
            onStateChange({
                uploadStatus: 'error',
                uploadMessage: message,
            });
        } finally {
            if (uploadAbortRef.current === controller) {
                uploadAbortRef.current = null;
            }
            uploadInFlightRef.current = false;
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
