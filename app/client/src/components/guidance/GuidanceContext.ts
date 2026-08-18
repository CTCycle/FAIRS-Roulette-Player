import { createContext, useContext } from 'react';
import type {
    GuidanceStatus,
    TipDefinition,
    TourDefinition,
} from './types';

export interface GuidanceContextValue {
    tipsOpen: boolean;
    activeTour: TourDefinition | null;
    activeTourStep: number;
    openTips: () => void;
    closeTips: () => void;
    startTour: (tour: TourDefinition) => void;
    nextTourStep: () => void;
    previousTourStep: () => void;
    dismissTour: () => void;
    getStatus: (id: string, version: number) => GuidanceStatus | undefined;
    markDismissed: (id: string, version: number) => void;
    tips: TipDefinition[];
}

export const GuidanceContext = createContext<GuidanceContextValue | undefined>(undefined);

export const useGuidance = (): GuidanceContextValue => {
    const context = useContext(GuidanceContext);
    if (!context) {
        throw new Error('useGuidance must be used inside GuidanceProvider');
    }
    return context;
};
