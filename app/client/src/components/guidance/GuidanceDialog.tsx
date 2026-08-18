import React, { useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { useDialogFocus } from './useDialogFocus';

interface GuidanceDialogProps {
    title: string;
    description?: string;
    labelledBy: string;
    onClose: () => void;
    children: React.ReactNode;
    className?: string;
}

export const GuidanceDialog: React.FC<GuidanceDialogProps> = ({
    title,
    description,
    labelledBy,
    onClose,
    children,
    className = '',
}) => {
    const dialogRef = useRef<HTMLDivElement>(null);
    useDialogFocus(dialogRef, onClose);

    if (typeof document === 'undefined') {
        return null;
    }

    return createPortal(
        <div className="guidance-dialog-layer">
            <div className="guidance-dialog-backdrop" onClick={onClose} aria-hidden="true" />
            <div
                ref={dialogRef}
                className={`guidance-dialog ${className}`.trim()}
                role="dialog"
                aria-modal="true"
                aria-labelledby={labelledBy}
                aria-describedby={description ? `${labelledBy}-description` : undefined}
                tabIndex={-1}
            >
                <div className="guidance-dialog-header">
                    <div>
                        <h2 id={labelledBy}>{title}</h2>
                        {description && <p id={`${labelledBy}-description`}>{description}</p>}
                    </div>
                    <button
                        type="button"
                        className="guidance-icon-button"
                        onClick={onClose}
                        aria-label={`Close ${title}`}
                        data-dialog-autofocus="true"
                    >
                        <X size={17} aria-hidden="true" />
                    </button>
                </div>
                {children}
            </div>
        </div>,
        document.body,
    );
};
