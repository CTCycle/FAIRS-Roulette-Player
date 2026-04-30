import { useCallback, useMemo, useState } from 'react';

interface UseWizardStepParams {
    initialStep?: number;
    totalSteps: number;
}

interface UseWizardStepResult {
    step: number;
    isFirstStep: boolean;
    isLastStep: boolean;
    setStep: (step: number) => void;
    resetStep: () => void;
    goToPreviousStep: () => void;
    goToNextStep: () => void;
}

const clampStep = (step: number, totalSteps: number): number => {
    const maxStep = Math.max(0, totalSteps - 1);
    return Math.min(maxStep, Math.max(0, step));
};

export const useWizardStep = ({ initialStep = 0, totalSteps }: UseWizardStepParams): UseWizardStepResult => {
    const [step, setCurrentStep] = useState(() => clampStep(initialStep, totalSteps));

    const setStep = useCallback((nextStep: number) => {
        setCurrentStep(clampStep(nextStep, totalSteps));
    }, [totalSteps]);

    const resetStep = useCallback(() => {
        setCurrentStep(clampStep(initialStep, totalSteps));
    }, [initialStep, totalSteps]);

    const goToPreviousStep = useCallback(() => {
        setCurrentStep((previous) => clampStep(previous - 1, totalSteps));
    }, [totalSteps]);

    const goToNextStep = useCallback(() => {
        setCurrentStep((previous) => clampStep(previous + 1, totalSteps));
    }, [totalSteps]);

    const isFirstStep = step === 0;
    const isLastStep = useMemo(() => step >= Math.max(0, totalSteps - 1), [step, totalSteps]);

    return {
        step,
        isFirstStep,
        isLastStep,
        setStep,
        resetStep,
        goToPreviousStep,
        goToNextStep,
    };
};
