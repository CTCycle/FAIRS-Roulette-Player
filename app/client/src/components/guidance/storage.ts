import type {
    GuidanceEntry,
    GuidanceStatus,
    GuidanceStorageState,
} from './types';

export const GUIDANCE_STORAGE_KEY = 'fairs.guidance';
export const GUIDANCE_SCHEMA_VERSION = 1;

export const createEmptyGuidanceState = (): GuidanceStorageState => ({
    schemaVersion: GUIDANCE_SCHEMA_VERSION,
    entries: {},
});

const isGuidanceStatus = (value: unknown): value is GuidanceStatus => (
    value === 'seen'
    || value === 'dismissed'
    || value === 'skipped'
    || value === 'completed'
);

const isGuidanceEntry = (value: unknown): value is GuidanceEntry => {
    if (typeof value !== 'object' || value === null) {
        return false;
    }

    const entry = value as Partial<GuidanceEntry>;
    return typeof entry.version === 'number'
        && Number.isInteger(entry.version)
        && entry.version > 0
        && isGuidanceStatus(entry.status);
};

export const readGuidanceState = (): GuidanceStorageState => {
    if (typeof window === 'undefined') {
        return createEmptyGuidanceState();
    }

    try {
        const raw = window.localStorage.getItem(GUIDANCE_STORAGE_KEY);
        if (!raw) {
            return createEmptyGuidanceState();
        }

        const parsed: unknown = JSON.parse(raw);
        if (typeof parsed !== 'object' || parsed === null) {
            return createEmptyGuidanceState();
        }

        const candidate = parsed as Partial<GuidanceStorageState>;
        if (candidate.schemaVersion !== GUIDANCE_SCHEMA_VERSION) {
            return createEmptyGuidanceState();
        }

        const rawEntries = candidate.entries;
        if (typeof rawEntries !== 'object' || rawEntries === null || Array.isArray(rawEntries)) {
            return createEmptyGuidanceState();
        }

        const entries = Object.fromEntries(
            Object.entries(rawEntries).filter(([, entry]) => isGuidanceEntry(entry)),
        ) as Record<string, GuidanceEntry>;

        return {
            schemaVersion: GUIDANCE_SCHEMA_VERSION,
            entries,
        };
    } catch {
        return createEmptyGuidanceState();
    }
};

export const writeGuidanceState = (state: GuidanceStorageState): void => {
    if (typeof window === 'undefined') {
        return;
    }

    try {
        window.localStorage.setItem(GUIDANCE_STORAGE_KEY, JSON.stringify(state));
    } catch {
        // Private browsing and managed browser policies can make storage unavailable.
        // Guidance remains usable for the current session in that case.
    }
};

export const getGuidanceStatus = (
    state: GuidanceStorageState,
    id: string,
    version: number,
): GuidanceStatus | undefined => {
    const entry = state.entries[id];
    return entry?.version === version ? entry.status : undefined;
};
