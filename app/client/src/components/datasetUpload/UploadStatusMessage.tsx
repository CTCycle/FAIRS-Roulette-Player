import React from 'react';
import type { DatasetUploadStatus } from '../../utils/datasetUpload';

interface UploadStatusMessageProps {
    uploadStatus: DatasetUploadStatus;
    uploadMessage: string;
}

const getMessageVariantClass = (uploadStatus: DatasetUploadStatus): string => {
    if (uploadStatus === 'success') {
        return 'upload-message-success';
    }
    if (uploadStatus === 'error') {
        return 'upload-message-error';
    }
    return 'upload-message-info';
};

export const UploadStatusMessage: React.FC<UploadStatusMessageProps> = ({
    uploadStatus,
    uploadMessage,
}) => {
    if (!uploadMessage) {
        return null;
    }

    return (
        <div
            className={`upload-message ${getMessageVariantClass(uploadStatus)}`}
            role="status"
            aria-live="polite"
        >
            {uploadMessage}
        </div>
    );
};
