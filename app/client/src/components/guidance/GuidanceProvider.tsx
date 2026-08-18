import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { GuidanceContext, type GuidanceContextValue } from './GuidanceContext';
import { GuidedTour } from './GuidedTour';
import { TipsAndTricksDialog } from './TipsAndTricksDialog';
import { TIPS } from './definitions';
import {
    getGuidanceStatus,
    readGuidanceState,
    writeGuidanceState,
} from './storage';
import type { GuidanceStatus, TourDefinition } from './types';
import './Guidance.css';

export const GuidanceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [storageState, setStorageState] = useState(readGuidanceState);
    const [tipsOpen, setTipsOpen] = useState(false);
    const [activeTour, setActiveTour] = useState<TourDefinition | null>(null);
    const [activeTourStep, setActiveTourStep] = useState(0);

    useEffect(() => {
        writeGuidanceState(storageState);
    }, [storageState]);

    const getStatus = useCallback((id: string, version: number): GuidanceStatus | undefined => (
        getGuidanceStatus(storageState, id, version)
    ), [storageState]);

    const updateStatus = useCallback((id: string, version: number, status: GuidanceStatus) => {
        setStorageState((current) => ({
            ...current,
            entries: {
                ...current.entries,
                [id]: { version, status },
            },
        }));
    }, []);

    const startTour = useCallback((tour: TourDefinition) => {
        setTipsOpen(false);
        setActiveTour(tour);
        setActiveTourStep(0);
        updateStatus(tour.id, tour.version, 'seen');
    }, [updateStatus]);

    const finishTour = useCallback((status: GuidanceStatus) => {
        if (activeTour) {
            updateStatus(activeTour.id, activeTour.version, status);
        }
        setActiveTour(null);
        setActiveTourStep(0);
    }, [activeTour, updateStatus]);

    const nextTourStep = useCallback(() => {
        if (!activeTour) {
            return;
        }
        if (activeTourStep >= activeTour.steps.length - 1) {
            updateStatus(activeTour.id, activeTour.version, 'completed');
            setActiveTour(null);
            setActiveTourStep(0);
            return;
        }
        setActiveTourStep((step) => step + 1);
    }, [activeTour, activeTourStep, updateStatus]);

    const previousTourStep = useCallback(() => {
        setActiveTourStep((step) => Math.max(0, step - 1));
    }, []);

    const markDismissed = useCallback((id: string, version: number) => {
        updateStatus(id, version, 'dismissed');
    }, [updateStatus]);

    const value = useMemo<GuidanceContextValue>(() => ({
        tipsOpen,
        activeTour,
        activeTourStep,
        openTips: () => setTipsOpen(true),
        closeTips: () => setTipsOpen(false),
        startTour,
        nextTourStep,
        previousTourStep,
        dismissTour: () => finishTour('dismissed'),
        getStatus,
        markDismissed,
        tips: TIPS,
    }), [
        activeTour,
        activeTourStep,
        finishTour,
        getStatus,
        markDismissed,
        nextTourStep,
        previousTourStep,
        startTour,
        tipsOpen,
    ]);

    return (
        <GuidanceContext.Provider value={value}>
            {children}
            <TipsAndTricksDialog open={tipsOpen} onClose={() => setTipsOpen(false)} />
            <GuidedTour />
        </GuidanceContext.Provider>
    );
};
