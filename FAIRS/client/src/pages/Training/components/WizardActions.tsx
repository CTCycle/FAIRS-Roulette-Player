import React from 'react';
import { Check, ChevronLeft, ChevronRight } from 'lucide-react';

interface WizardActionsProps {
    isFirstStep: boolean;
    isLastStep: boolean;
    isSubmitting: boolean;
    onCancel: () => void;
    onPrevious: () => void;
    onNext: () => void;
    onConfirm: () => void;
}

export const WizardActions: React.FC<WizardActionsProps> = ({
    isFirstStep,
    isLastStep,
    isSubmitting,
    onCancel,
    onPrevious,
    onNext,
    onConfirm,
}) => {
    return (
        <div className="wizard-actions">
            <button
                type="button"
                className="wizard-btn wizard-btn-secondary"
                onClick={onCancel}
                disabled={isSubmitting}
            >
                Cancel
            </button>
            <div className="wizard-actions-right">
                <button
                    type="button"
                    className="wizard-btn wizard-btn-secondary"
                    onClick={onPrevious}
                    disabled={isFirstStep || isSubmitting}
                >
                    <ChevronLeft size={16} />
                    Previous
                </button>
                {!isLastStep ? (
                    <button
                        type="button"
                        className="wizard-btn wizard-btn-primary"
                        onClick={onNext}
                        disabled={isSubmitting}
                    >
                        Next
                        <ChevronRight size={16} />
                    </button>
                ) : (
                    <button
                        type="button"
                        className="wizard-btn wizard-btn-primary"
                        onClick={onConfirm}
                        disabled={isSubmitting}
                    >
                        <Check size={16} />
                        Confirm
                    </button>
                )}
            </div>
        </div>
    );
};
