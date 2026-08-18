import type { ReactNode } from 'react';

export type GuidanceStatus = 'seen' | 'dismissed' | 'skipped' | 'completed';

export interface GuidanceEntry {
    version: number;
    status: GuidanceStatus;
}

export interface GuidanceStorageState {
    schemaVersion: number;
    entries: Record<string, GuidanceEntry>;
}

export interface TourStep {
    id: string;
    target: string;
    title: string;
    body: string;
}

export interface TourDefinition {
    id: string;
    version: number;
    title: string;
    route: string;
    steps: TourStep[];
}

export interface TipDefinition {
    id: string;
    title: string;
    body: string;
    actionLabel?: string;
    action?: ReactNode;
}
