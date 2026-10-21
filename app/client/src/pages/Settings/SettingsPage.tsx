// Copyright © 2023 Thomas Virdis
// Licensed under the MIT License.

import { useCallback, useEffect, useRef, useState } from 'react';
import type { SettingsPatchRequest, SettingsResponse } from '../../generated/api';
import { isAbortError } from '../../utils/apiClient';
import { fetchSettings, resetSettings, updateSettings } from '../../utils/settingsApi';
import DatabaseSettingsSection from './DatabaseSettingsSection';
import './SettingsPage.css';

interface ValidationErrors {
    pollingInterval?: string;
    jitBackend?: string;
    minimumNumber?: string;
    maximumNumber?: string;
    rouletteRange?: string;
}

interface SettingsDraft {
    minimumNumber: string;
    maximumNumber: string;
    excludeZero: boolean;
    invertColors: boolean;
    showNumberLabels: boolean;
    pollingInterval: string;
    jitCompile: boolean;
    jitBackend: string;
}

const EMPTY_DRAFT: SettingsDraft = {
    minimumNumber: '',
    maximumNumber: '',
    excludeZero: false,
    invertColors: false,
    showNumberLabels: true,
    pollingInterval: '',
    jitCompile: false,
    jitBackend: '',
};

const AUTOSAVE_DEBOUNCE_MS = 350;

const mergeSettingsPatches = (
    current: SettingsPatchRequest,
    next: SettingsPatchRequest,
): SettingsPatchRequest => ({
    ...current,
    ...next,
    jobs: current.jobs || next.jobs
        ? { ...(current.jobs ?? {}), ...(next.jobs ?? {}) }
        : undefined,
    device: current.device || next.device
        ? { ...(current.device ?? {}), ...(next.device ?? {}) }
        : undefined,
    roulette: current.roulette || next.roulette
        ? { ...(current.roulette ?? {}), ...(next.roulette ?? {}) }
        : undefined,
});

const hasSettingsPatch = (patch: SettingsPatchRequest): boolean => (
    Boolean(patch.jobs && Object.keys(patch.jobs).length)
    || Boolean(patch.device && Object.keys(patch.device).length)
    || Boolean(patch.roulette && Object.keys(patch.roulette).length)
);

type SettingsSection = 'roulette' | 'appearance' | 'runtime' | 'advanced' | 'database';

const SETTINGS_ERROR = 'Unable to load settings.';
const SETTINGS_SECTIONS: Array<{ id: SettingsSection; label: string }> = [
    { id: 'roulette', label: 'Roulette' },
    { id: 'appearance', label: 'Appearance' },
    { id: 'runtime', label: 'Runtime' },
    { id: 'advanced', label: 'Advanced' },
    { id: 'database', label: 'Database' },
];

const SettingsPage: React.FC = () => {
    const [savedSettings, setSavedSettings] = useState<SettingsResponse | null>(null);
    const [activeSection, setActiveSection] = useState<SettingsSection>(() => (
        new URLSearchParams(window.location.search).get('section') === 'database'
            ? 'database'
            : 'roulette'
    ));
    const [draft, setDraft] = useState<SettingsDraft>(EMPTY_DRAFT);
    const [loading, setLoading] = useState(true);
    const [resetting, setResetting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
    const draftRef = useRef(draft);
    const pendingPatchRef = useRef<SettingsPatchRequest>({});
    const saveWorkerRef = useRef<Promise<boolean> | null>(null);
    const debounceTimerRef = useRef<number | null>(null);
    const {
        minimumNumber,
        maximumNumber,
        excludeZero,
        invertColors,
        showNumberLabels,
        pollingInterval,
        jitCompile,
        jitBackend,
    } = draft;

    const clearSaveTimer = () => {
        if (debounceTimerRef.current !== null) {
            window.clearTimeout(debounceTimerRef.current);
            debounceTimerRef.current = null;
        }
    };

    const removePendingRouletteRange = () => {
        const pending = pendingPatchRef.current;
        if (!pending.roulette) return;
        const roulette = { ...pending.roulette };
        delete roulette.minimum_number;
        delete roulette.maximum_number;
        delete roulette.exclude_zero;
        pendingPatchRef.current = {
            ...pending,
            roulette: Object.keys(roulette).length > 0 ? roulette : undefined,
        };
    };

    const removePendingField = (section: 'jobs' | 'device') => {
        const pending = pendingPatchRef.current;
        if (section === 'jobs') {
            const jobs = { ...(pending.jobs ?? {}) };
            delete jobs.polling_interval;
            pendingPatchRef.current = {
                ...pending,
                jobs: Object.keys(jobs).length > 0 ? jobs : undefined,
            };
            return;
        }
        const device = { ...(pending.device ?? {}) };
        delete device.jit_backend;
        pendingPatchRef.current = {
            ...pending,
            device: Object.keys(device).length > 0 ? device : undefined,
        };
    };

    const runSaveWorker = useCallback((): Promise<boolean> => {
        if (saveWorkerRef.current) {
            return saveWorkerRef.current;
        }

        const worker = (async () => {
            let wroteSettings = false;
            while (hasSettingsPatch(pendingPatchRef.current)) {
                if (debounceTimerRef.current !== null) return true;
                const patch = pendingPatchRef.current;
                pendingPatchRef.current = {};
                try {
                    const settings = await updateSettings(patch);
                    setSavedSettings(settings);
                    wroteSettings = true;
                } catch (requestError) {
                    const retryNewerPending = hasSettingsPatch(pendingPatchRef.current)
                        && debounceTimerRef.current === null;
                    pendingPatchRef.current = mergeSettingsPatches(
                        patch,
                        pendingPatchRef.current,
                    );
                    setSuccessMessage(null);
                    const detail = requestError instanceof Error
                        ? requestError.message
                        : 'Unable to save settings.';
                    setError(`Change not saved. ${detail} The edited value is still shown here.`);
                    if (retryNewerPending) continue;
                    return false;
                }
            }
            if (wroteSettings && debounceTimerRef.current === null && !hasSettingsPatch(pendingPatchRef.current)) {
                setError(null);
                setSuccessMessage('Changes saved.');
            }
            return true;
        })();
        saveWorkerRef.current = worker;
        void worker.finally(() => {
            if (saveWorkerRef.current === worker) saveWorkerRef.current = null;
        });
        return worker;
    }, []);

    const scheduleSettingsPatch = (
        patch: SettingsPatchRequest,
        debounce = false,
    ) => {
        pendingPatchRef.current = mergeSettingsPatches(pendingPatchRef.current, patch);
        clearSaveTimer();
        if (debounce) {
            debounceTimerRef.current = window.setTimeout(() => {
                debounceTimerRef.current = null;
                void runSaveWorker();
            }, AUTOSAVE_DEBOUNCE_MS);
        } else {
            void runSaveWorker();
        }
    };

    const flushSettings = async (): Promise<boolean> => {
        clearSaveTimer();
        while (true) {
            if (hasSettingsPatch(pendingPatchRef.current)) {
                const saved = await runSaveWorker();
                if (!saved) return false;
                continue;
            }
            if (saveWorkerRef.current) {
                const saved = await saveWorkerRef.current;
                if (!saved) return false;
                continue;
            }
            return true;
        }
    };

    const updateDraft = (
        update: (current: SettingsDraft) => SettingsDraft,
    ): SettingsDraft => {
        const next = update(draftRef.current);
        draftRef.current = next;
        setDraft(next);
        return next;
    };

    const validateRouletteDraft = (current: SettingsDraft): ValidationErrors => {
        const nextErrors: ValidationErrors = {};
        const minimum = Number(current.minimumNumber);
        const maximum = Number(current.maximumNumber);
        if (!current.minimumNumber.trim()) {
            nextErrors.minimumNumber = 'Enter a minimum number.';
        } else if (!Number.isInteger(minimum) || minimum < 0 || minimum > 36) {
            nextErrors.minimumNumber = 'Use a whole number from 0 to 36.';
        }
        if (!current.maximumNumber.trim()) {
            nextErrors.maximumNumber = 'Enter a maximum number.';
        } else if (!Number.isInteger(maximum) || maximum < 0 || maximum > 36) {
            nextErrors.maximumNumber = 'Use a whole number from 0 to 36.';
        }
        if (!nextErrors.minimumNumber && !nextErrors.maximumNumber) {
            if (minimum > maximum) {
                nextErrors.rouletteRange = 'Minimum number cannot be greater than maximum number.';
            } else if (current.excludeZero && minimum === 0 && maximum === 0) {
                nextErrors.rouletteRange = 'Excluding zero would leave the roulette number pool empty.';
            }
        }
        return nextErrors;
    };

    const updateRouletteRange = (
        update: (current: SettingsDraft) => SettingsDraft,
        debounce: boolean,
    ) => {
        const next = updateDraft(update);
        const rangeErrors = validateRouletteDraft(next);
        setValidationErrors((current) => ({
            ...current,
            minimumNumber: rangeErrors.minimumNumber,
            maximumNumber: rangeErrors.maximumNumber,
            rouletteRange: rangeErrors.rouletteRange,
        }));
        setSuccessMessage(null);
        if (rangeErrors.minimumNumber || rangeErrors.maximumNumber || rangeErrors.rouletteRange) {
            removePendingRouletteRange();
            return;
        }
        scheduleSettingsPatch({
            roulette: {
                minimum_number: Number(next.minimumNumber),
                maximum_number: Number(next.maximumNumber),
                exclude_zero: next.excludeZero,
            },
        }, debounce);
    };

    const synchronizeDraft = useCallback((settings: SettingsResponse) => {
        setSavedSettings(settings);
        const nextDraft: SettingsDraft = {
            minimumNumber: String(settings.roulette.minimum_number),
            maximumNumber: String(settings.roulette.maximum_number),
            excludeZero: settings.roulette.exclude_zero,
            invertColors: settings.roulette.invert_colors,
            showNumberLabels: settings.roulette.show_number_labels,
            pollingInterval: String(settings.jobs.polling_interval),
            jitCompile: settings.device.jit_compile,
            jitBackend: settings.device.jit_backend,
        };
        draftRef.current = nextDraft;
        setDraft(nextDraft);
        setValidationErrors({});
    }, []);

    const loadSettings = useCallback(async (signal?: AbortSignal) => {
        await Promise.resolve();
        setLoading(true);
        setError(null);
        setSuccessMessage(null);
        try {
            const settings = await fetchSettings(signal);
            if (!signal?.aborted) {
                synchronizeDraft(settings);
            }
        } catch (requestError) {
            if (!isAbortError(requestError) && !signal?.aborted) {
                setError(requestError instanceof Error ? requestError.message : SETTINGS_ERROR);
            }
        } finally {
            if (!signal?.aborted) {
                setLoading(false);
            }
        }
    }, [synchronizeDraft]);

    useEffect(() => {
        const controller = new AbortController();

        void fetchSettings(controller.signal)
            .then((settings) => {
                if (!controller.signal.aborted) {
                    synchronizeDraft(settings);
                }
            })
            .catch((requestError: unknown) => {
                if (!isAbortError(requestError) && !controller.signal.aborted) {
                    setError(requestError instanceof Error ? requestError.message : SETTINGS_ERROR);
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            });

        return () => controller.abort();
    }, [synchronizeDraft]);

    const handleReset = async () => {
        clearSaveTimer();
        setError(null);
        setSuccessMessage(null);
        setResetting(true);
        try {
            const pendingChangesSaved = await flushSettings();
            if (!pendingChangesSaved) {
                setError('Unable to reset settings until the pending change has been saved. The edited value is still shown here.');
                return;
            }
            const settings = await resetSettings();
            synchronizeDraft(settings);
            setSuccessMessage('Settings reset to defaults.');
        } catch (requestError) {
            setError(requestError instanceof Error
                ? `Unable to reset settings. ${requestError.message}`
                : 'Unable to reset settings.');
        } finally {
            setResetting(false);
        }
    };

    const isBusy = loading || resetting;

    return (
        <div className="settings-page page-shell">
            {loading && <div className="settings-feedback" role="status">Loading settings…</div>}
            {error && (
                <div className="settings-feedback settings-feedback-error" role="alert">
                    <span>{error}</span>
                    {!savedSettings && (
                        <button type="button" className="settings-link-button" onClick={() => void loadSettings()}>
                            Try again
                        </button>
                    )}
                </div>
            )}
            {successMessage && <div className="settings-feedback settings-feedback-success settings-feedback-compact" role="status">{successMessage}</div>}

            {!savedSettings && (
                <div className="settings-layout">
                    <nav className="settings-navigation" aria-label="Settings categories">
                        <button
                            id="settings-nav-database"
                            type="button"
                            className="settings-navigation-item settings-navigation-item-active"
                            aria-current="page"
                            aria-controls="settings-panel-database"
                            disabled={isBusy}
                        >
                            Database
                        </button>
                    </nav>
                    <div className="settings-content">
                        <DatabaseSettingsSection
                            active
                            onBeforeSwitch={flushSettings}
                            onSettingsReloaded={synchronizeDraft}
                        />
                    </div>
                </div>
            )}

            {savedSettings && (
                <div className="settings-form">
                    <div className="settings-layout">
                        <nav className="settings-navigation" aria-label="Settings categories">
                            {SETTINGS_SECTIONS.map((section) => (
                            <button
                                key={section.id}
                                id={`settings-nav-${section.id}`}
                                type="button"
                                className={`settings-navigation-item${activeSection === section.id ? ' settings-navigation-item-active' : ''}`}
                                aria-current={activeSection === section.id ? 'page' : undefined}
                                aria-controls={`settings-panel-${section.id}`}
                                onClick={() => setActiveSection(section.id)}
                                disabled={isBusy}
                            >
                                {section.label}
                            </button>
                        ))}
                        </nav>

                        <div className="settings-content">

                    {activeSection === 'roulette' && (
                        <section
                            id="settings-panel-roulette"
                            className="settings-panel"
                            aria-labelledby="settings-nav-roulette"
                        >
                            <div className="settings-section-header">
                                <div>
                                    <h2>Roulette numbers</h2>
                                </div>
                                <p>Configure the number range used for generated data and live observations.</p>
                            </div>

                            <div className="settings-field-row">
                                <div className="settings-field-copy">
                                    <span className="settings-field-title">Number range</span>
                                    <p id="settings-range-help">Set the inclusive range for new runs. Values outside it are ignored.</p>
                                </div>
                                <div className="settings-field-control">
                                    <div className="settings-range-grid">
                                        <label htmlFor="settings-minimum-number">
                                            <span>Minimum</span>
                                            <input
                                                id="settings-minimum-number"
                                                className="settings-input"
                                                type="number"
                                                min="0"
                                                max="36"
                                                step="1"
                                                value={minimumNumber}
                                                onChange={(event) => {
                                                    updateRouletteRange(
                                                        (current) => ({ ...current, minimumNumber: event.target.value }),
                                                        true,
                                                    );
                                                }}
                                                aria-describedby="settings-range-help settings-minimum-error settings-range-error"
                                                aria-invalid={Boolean(validationErrors.minimumNumber || validationErrors.rouletteRange)}
                                                disabled={isBusy}
                                            />
                                        </label>
                                        <label htmlFor="settings-maximum-number">
                                            <span>Maximum</span>
                                            <input
                                                id="settings-maximum-number"
                                                className="settings-input"
                                                type="number"
                                                min="0"
                                                max="36"
                                                step="1"
                                                value={maximumNumber}
                                                onChange={(event) => {
                                                    updateRouletteRange(
                                                        (current) => ({ ...current, maximumNumber: event.target.value }),
                                                        true,
                                                    );
                                                }}
                                                aria-describedby="settings-range-help settings-maximum-error settings-range-error"
                                                aria-invalid={Boolean(validationErrors.maximumNumber || validationErrors.rouletteRange)}
                                                disabled={isBusy}
                                            />
                                        </label>
                                    </div>
                                    {validationErrors.minimumNumber && (
                                        <span id="settings-minimum-error" className="settings-field-error">{validationErrors.minimumNumber}</span>
                                    )}
                                    {validationErrors.maximumNumber && (
                                        <span id="settings-maximum-error" className="settings-field-error">{validationErrors.maximumNumber}</span>
                                    )}
                                    {validationErrors.rouletteRange && (
                                        <span id="settings-range-error" className="settings-field-error">{validationErrors.rouletteRange}</span>
                                    )}
                                </div>
                            </div>

                            <div className="settings-field-row settings-checkbox-row">
                                <div className="settings-field-copy">
                                    <label htmlFor="settings-exclude-zero">Include zero</label>
                                    <p id="settings-exclude-zero-help">Allow zero in generated outcomes and live observations.</p>
                                </div>
                                <div className="settings-field-control">
                                    <label className="settings-checkbox-label" htmlFor="settings-exclude-zero">
                                        <input
                                            id="settings-exclude-zero"
                                            type="checkbox"
                                            checked={!excludeZero}
                                            onChange={(event) => {
                                                updateRouletteRange(
                                                    (current) => ({ ...current, excludeZero: !event.target.checked }),
                                                    false,
                                                );
                                            }}
                                            aria-describedby="settings-exclude-zero-help"
                                            disabled={isBusy}
                                        />
                                        <span>{excludeZero ? 'Zero excluded' : 'Zero included'}</span>
                                    </label>
                                </div>
                            </div>
                        </section>
                    )}

                    {activeSection === 'appearance' && (
                        <section
                            id="settings-panel-appearance"
                            className="settings-panel"
                            aria-labelledby="settings-nav-appearance"
                        >
                            <div className="settings-section-header">
                                <div>
                                    <h2>Roulette appearance</h2>
                                </div>
                                <p>Choose how newly rendered roulette wheel frames are displayed.</p>
                            </div>

                            <div className="settings-field-row settings-checkbox-row">
                                <div className="settings-field-copy">
                                    <label htmlFor="settings-invert-colors">Invert colors</label>
                                    <p id="settings-invert-colors-help">Swap red and black wheel slices; zero stays green.</p>
                                </div>
                                <div className="settings-field-control">
                                    <label className="settings-checkbox-label" htmlFor="settings-invert-colors">
                                        <input
                                            id="settings-invert-colors"
                                            type="checkbox"
                                            checked={invertColors}
                                            onChange={(event) => {
                                                const next = updateDraft((current) => ({ ...current, invertColors: event.target.checked }));
                                                setSuccessMessage(null);
                                                scheduleSettingsPatch({ roulette: { invert_colors: next.invertColors } });
                                            }}
                                            aria-describedby="settings-invert-colors-help"
                                            disabled={isBusy}
                                        />
                                        <span>{invertColors ? 'Inverted' : 'Standard'}</span>
                                    </label>
                                </div>
                            </div>

                            <div className="settings-field-row settings-checkbox-row">
                                <div className="settings-field-copy">
                                    <label htmlFor="settings-show-number-labels">Show number labels</label>
                                    <p id="settings-show-number-labels-help">Show number labels on rendered roulette wheels.</p>
                                </div>
                                <div className="settings-field-control">
                                    <label className="settings-checkbox-label" htmlFor="settings-show-number-labels">
                                        <input
                                            id="settings-show-number-labels"
                                            type="checkbox"
                                            checked={showNumberLabels}
                                            onChange={(event) => {
                                                const next = updateDraft((current) => ({ ...current, showNumberLabels: event.target.checked }));
                                                setSuccessMessage(null);
                                                scheduleSettingsPatch({ roulette: { show_number_labels: next.showNumberLabels } });
                                            }}
                                            aria-describedby="settings-show-number-labels-help"
                                            disabled={isBusy}
                                        />
                                        <span>{showNumberLabels ? 'Visible' : 'Hidden'}</span>
                                    </label>
                                </div>
                            </div>
                        </section>
                    )}

                    {activeSection === 'runtime' && (
                        <section
                            id="settings-panel-runtime"
                            className="settings-panel"
                            aria-labelledby="settings-nav-runtime"
                        >
                            <div className="settings-section-header">
                                <div>
                                    <h2>Training polling</h2>
                                </div>
                                <p>Set the polling cadence for future training runs.</p>
                            </div>
                            <div className="settings-field-row">
                                <div className="settings-field-copy">
                                    <label htmlFor="settings-polling-interval">Polling interval</label>
                                    <p id="settings-polling-help">Running workers keep their existing interval.</p>
                                </div>
                                <div className="settings-field-control settings-number-control">
                                    <input
                                        id="settings-polling-interval"
                                        className="settings-input"
                                        type="number"
                                        min="0.1"
                                        max="10"
                                        step="0.1"
                                        value={pollingInterval}
                                        onChange={(event) => {
                                            const value = event.target.value;
                                            updateDraft((current) => ({ ...current, pollingInterval: value }));
                                            setSuccessMessage(null);
                                            const interval = Number(value);
                                            const valid = Boolean(value.trim())
                                                && Number.isFinite(interval)
                                                && interval >= 0.1
                                                && interval <= 10;
                                            setValidationErrors((current) => ({
                                                ...current,
                                                pollingInterval: valid
                                                    ? undefined
                                                    : 'Use a value from 0.1 to 10 seconds.',
                                            }));
                                            if (valid) {
                                                scheduleSettingsPatch({ jobs: { polling_interval: interval } }, true);
                                            } else {
                                                removePendingField('jobs');
                                            }
                                        }}
                                        onBlur={() => void flushSettings()}
                                        aria-describedby="settings-polling-help settings-polling-error"
                                        aria-invalid={Boolean(validationErrors.pollingInterval)}
                                        disabled={isBusy}
                                    />
                                    <span>seconds</span>
                                    {validationErrors.pollingInterval && (
                                        <span id="settings-polling-error" className="settings-field-error">{validationErrors.pollingInterval}</span>
                                    )}
                                </div>
                            </div>
                        </section>
                    )}

                    {activeSection === 'advanced' && (
                        <section
                            id="settings-panel-advanced"
                            className="settings-panel"
                            aria-labelledby="settings-nav-advanced"
                        >
                            <div className="settings-section-header">
                                <div>
                                    <h2>JIT model construction</h2>
                                </div>
                                <p>Apply these settings to newly constructed training models.</p>
                            </div>
                            <div className="settings-field-row settings-checkbox-row">
                                <div className="settings-field-copy">
                                    <label htmlFor="settings-jit-compile">Enable JIT compilation</label>
                                    <p id="settings-jit-compile-help">Use the selected backend for new training models.</p>
                                </div>
                                <div className="settings-field-control">
                                    <label className="settings-checkbox-label" htmlFor="settings-jit-compile">
                                        <input
                                            id="settings-jit-compile"
                                            type="checkbox"
                                            checked={jitCompile}
                                            onChange={(event) => {
                                                const next = updateDraft((current) => ({ ...current, jitCompile: event.target.checked }));
                                                setSuccessMessage(null);
                                                scheduleSettingsPatch({ device: { jit_compile: next.jitCompile } });
                                            }}
                                            aria-describedby="settings-jit-compile-help"
                                            disabled={isBusy}
                                        />
                                        <span>{jitCompile ? 'Enabled' : 'Disabled'}</span>
                                    </label>
                                </div>
                            </div>
                            <div className="settings-field-row">
                                <div className="settings-field-copy">
                                    <label htmlFor="settings-jit-backend">JIT backend</label>
                                    <p id="settings-jit-backend-help">Saved while JIT is off. Windows supports <code>eager</code>; <code>inductor</code> requires Triton on supported platforms.</p>
                                </div>
                                <div className="settings-field-control">
                                    <input
                                        id="settings-jit-backend"
                                        className="settings-input"
                                        type="text"
                                        value={jitBackend}
                                        onChange={(event) => {
                                            const value = event.target.value;
                                            updateDraft((current) => ({ ...current, jitBackend: value }));
                                            setSuccessMessage(null);
                                            if (value.trim()) {
                                                setValidationErrors((current) => ({ ...current, jitBackend: undefined }));
                                                scheduleSettingsPatch({ device: { jit_backend: value.trim() } }, true);
                                            } else {
                                                setValidationErrors((current) => ({
                                                    ...current,
                                                    jitBackend: 'Enter a JIT backend name.',
                                                }));
                                                removePendingField('device');
                                            }
                                        }}
                                        onBlur={() => void flushSettings()}
                                        aria-describedby="settings-jit-backend-help settings-jit-backend-error"
                                        aria-invalid={Boolean(validationErrors.jitBackend)}
                                        disabled={!jitCompile || isBusy}
                                    />
                                    {validationErrors.jitBackend && (
                                        <span id="settings-jit-backend-error" className="settings-field-error">{validationErrors.jitBackend}</span>
                                    )}
                                </div>
                            </div>
                        </section>
                    )}

                    <DatabaseSettingsSection
                        active={activeSection === 'database'}
                        onBeforeSwitch={flushSettings}
                        onSettingsReloaded={synchronizeDraft}
                    />

                        </div>
                    </div>

                    {activeSection !== 'database' && <div className="settings-actions">
                        <button type="button" className="settings-button settings-button-secondary" onClick={() => void handleReset()} disabled={isBusy}>
                            {resetting ? 'Resetting…' : 'Reset to defaults'}
                        </button>
                    </div>}
                </div>
            )}
        </div>
    );
};

export default SettingsPage;
