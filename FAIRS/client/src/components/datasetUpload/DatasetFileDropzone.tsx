import React from 'react';
import type { ChangeEvent, DragEvent, ReactNode, RefObject } from 'react';
import { useKeyboardActivation } from '../../hooks/useKeyboardActivation';

interface DatasetFileDropzoneProps {
    className?: string;
    ariaLabel: string;
    fileInputRef: RefObject<HTMLInputElement | null>;
    onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
    onDragOver: (event: DragEvent<HTMLElement>) => void;
    onDrop: (event: DragEvent<HTMLElement>) => void;
    children: ReactNode;
}

export const DatasetFileDropzone: React.FC<DatasetFileDropzoneProps> = ({
    className = 'upload-area',
    ariaLabel,
    fileInputRef,
    onFileChange,
    onDragOver,
    onDrop,
    children,
}) => {
    const openFilePicker = (): void => {
        fileInputRef.current?.click();
    };
    const handleKeyDown = useKeyboardActivation(openFilePicker);

    return (
        <div
            className={className}
            role="button"
            tabIndex={0}
            onClick={openFilePicker}
            onKeyDown={handleKeyDown}
            onDragOver={onDragOver}
            onDrop={onDrop}
            aria-label={ariaLabel}
        >
            {children}
            <input
                type="file"
                ref={fileInputRef}
                onChange={onFileChange}
                className="hidden-file-input"
                accept=".csv,.xlsx,.xls"
            />
        </div>
    );
};
