import { useCallback, useEffect, useMemo, useState } from 'react';
import type { SettingsPatchRequest, SettingsResponse } from '../../generated/api';
import { isAbortError } from '../../utils/apiClient';
import { fetchSettings, resetSettings, updateSettings } from '../../utils/settingsApi';
import './SettingsPage.css';

interface ValidationErrors {
    pollingInterval?: string;
    jitBackend?: string;
    minimumNumber?: string;
    maximumNumber?: string;
    rouletteRange?: string;
}

type SettingsTab = 'roulette' | 'appearance' | 'runtime' | 'advanced';

const SETTINGS_ERROR = 'Unable to load settings.';
const SETTINGS_TABS: Array<{ id: SettingsTab; label: string }> = [
    { id: 'roulette', label: 'Roulette' },
    { id: 'appearance', label: 'Appearance' },
    { id: 'runtime', label: 'Runtime' },
    { id: 'advanced', label: 'Advanced' },
];

const SettingsPage: React.FC = () => {
    const [savedSettings, setSavedSettings] = useState<SettingsResponse | null>(null);
    const [activeTab, setActiveTab] = useState<SettingsTab>('roulette');
    const [minimumNumber, setMinimumNumber] = useState('');
    const [maximumNumber, setMaximumNumber] = useState('');
    const [excludeZero, setExcludeZero] = useState(false);
    const [invertColors, setInvertColors] = useState(false);
    const [showNumberLabels, setShowNumberLabels] = useState(true);
    const [pollingInterval, setPollingInterval] = useState('');
    const [jitCompile, setJitCompile] = useState(false);
    const [jitBackend, setJitBackend] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [resetting, setResetting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});

    const synchronizeDraft = useCallback((settings: SettingsResponse) => {
        setSavedSettings(settings);
        setMinimumNumber(String(settings.roulette.minimum_number));
        setMaximumNumber(String(settings.roulette.maximum_number));
        setExcludeZero(settings.roulette.exclude_zero);
        setInvertColors(settings.roulette.invert_colors);
        setShowNumberLabels(settings.roulette.show_number_labels);
        setPollingInterval(String(settings.jobs.polling_interval));
        setJitCompile(settings.device.jit_compile);
        setJitBackend(settings.device.jit_backend);
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

    const dirtyFields = useMemo(() => {
        if (!savedSettings) {
            return {
                minimumNumber: false,
                maximumNumber: false,
                excludeZero: false,
                invertColors: false,
                showNumberLabels: false,
                polling: false,
                jitCompile: false,
                jitBackend: false,
            };
        }
        return {
            minimumNumber: minimumNumber !== String(savedSettings.roulette.minimum_number),
            maximumNumber: maximumNumber !== String(savedSettings.roulette.maximum_number),
            excludeZero: excludeZero !== savedSettings.roulette.exclude_zero,
            invertColors: invertColors !== savedSettings.roulette.invert_colors,
            showNumberLabels: showNumberLabels !== savedSettings.roulette.show_number_labels,
            polling: Number(pollingInterval) !== savedSettings.jobs.polling_interval,
            jitCompile: jitCompile !== savedSettings.device.jit_compile,
            jitBackend: jitBackend.trim() !== savedSettings.device.jit_backend,
        };
    }, [
        excludeZero,
        invertColors,
        jitBackend,
        jitCompile,
        maximumNumber,
        minimumNumber,
        pollingInterval,
        savedSettings,
        showNumberLabels,
    ]);

    const rouletteDirty = dirtyFields.minimumNumber
        || dirtyFields.maximumNumber
        || dirtyFields.excludeZero
        || dirtyFields.invertColors
        || dirtyFields.showNumberLabels;
    const isDirty = rouletteDirty
        || dirtyFields.polling
        || dirtyFields.jitCompile
        || dirtyFields.jitBackend;
    const isBusy = loading || saving || resetting;

    const validateDraft = (): ValidationErrors => {
        const nextErrors: ValidationErrors = {};
        const minimum = Number(minimumNumber);
        const maximum = Number(maximumNumber);

        if (!minimumNumber.trim()) {
            nextErrors.minimumNumber = 'Enter a minimum number.';
        } else if (!Number.isInteger(minimum) || minimum < 0 || minimum > 36) {
            nextErrors.minimumNumber = 'Use a whole number from 0 to 36.';
        }
        if (!maximumNumber.trim()) {
            nextErrors.maximumNumber = 'Enter a maximum number.';
        } else if (!Number.isInteger(maximum) || maximum < 0 || maximum > 36) {
            nextErrors.maximumNumber = 'Use a whole number from 0 to 36.';
        }
        if (!nextErrors.minimumNumber && !nextErrors.maximumNumber) {
            if (minimum > maximum) {
                nextErrors.rouletteRange = 'Minimum number cannot be greater than maximum number.';
            } else if (excludeZero && minimum === 0 && maximum === 0) {
                nextErrors.rouletteRange = 'Excluding zero would leave the roulette number pool empty.';
            }
        }

        if (!pollingInterval.trim()) {
            nextErrors.pollingInterval = 'Enter a polling interval.';
        } else {
            const value = Number(pollingInterval);
            if (!Number.isFinite(value) || value < 0.1 || value > 10) {
                nextErrors.pollingInterval = 'Use a value from 0.1 to 10 seconds.';
            }
        }
        if (!jitBackend.trim()) {
            nextErrors.jitBackend = 'Enter a JIT backend name.';
        }
        setValidationErrors(nextErrors);
        if (nextErrors.minimumNumber || nextErrors.maximumNumber || nextErrors.rouletteRange) {
            setActiveTab('roulette');
        } else if (nextErrors.pollingInterval) {
            setActiveTab('runtime');
        } else if (nextErrors.jitBackend) {
            setActiveTab('advanced');
        }
        return nextErrors;
    };

    const clearRangeValidation = () => {
        setValidationErrors((current) => ({
            ...current,
            minimumNumber: undefined,
            maximumNumber: undefined,
            rouletteRange: undefined,
        }));
    };

    const handleSave = async () => {
        setError(null);
        setSuccessMessage(null);
        const nextErrors = validateDraft();
        if (Object.keys(nextErrors).length > 0 || !savedSettings || !isDirty) {
            return;
        }

        const patch: SettingsPatchRequest = {};
        if (rouletteDirty) {
            patch.roulette = {};
            if (dirtyFields.minimumNumber) {
                patch.roulette.minimum_number = Number(minimumNumber);
            }
            if (dirtyFields.maximumNumber) {
                patch.roulette.maximum_number = Number(maximumNumber);
            }
            if (dirtyFields.excludeZero) {
                patch.roulette.exclude_zero = excludeZero;
            }
            if (dirtyFields.invertColors) {
                patch.roulette.invert_colors = invertColors;
            }
            if (dirtyFields.showNumberLabels) {
                patch.roulette.show_number_labels = showNumberLabels;
            }
        }
        if (dirtyFields.polling) {
            patch.jobs = { polling_interval: Number(pollingInterval) };
        }
        if (dirtyFields.jitCompile || dirtyFields.jitBackend) {
            patch.device = {};
            if (dirtyFields.jitCompile) {
                patch.device.jit_compile = jitCompile;
            }
            if (dirtyFields.jitBackend) {
                patch.device.jit_backend = jitBackend.trim();
            }
        }

        setSaving(true);
        try {
            const settings = await updateSettings(patch);
            synchronizeDraft(settings);
            setSuccessMessage('Settings saved.');
        } catch (requestError) {
            if (!isAbortError(requestError)) {
                setError(requestError instanceof Error ? requestError.message : 'Unable to save settings.');
            }
        } finally {
            setSaving(false);
        }
    };

    const handleReset = async () => {
        setError(null);
        setSuccessMessage(null);
        setResetting(true);
        try {
            const settings = await resetSettings();
            synchronizeDraft(settings);
            setSuccessMessage('Settings reset to defaults.');
        } catch (requestError) {
            if (!isAbortError(requestError)) {
                setError(requestError instanceof Error ? requestError.message : 'Unable to reset settings.');
            }
        } finally {
            setResetting(false);
        }
    };

    return (
        <div className="settings-page page-shell">
            <header className="page-header">
                <p className="page-eyebrow">Workspace settings</p>
                <h1>Settings</h1>
                <p className="page-subtitle">
                    Configure application-wide roulette behavior, appearance, and technical runtime settings without editing JSON files.
                </p>
            </header>

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
            {successMessage && <div className="settings-feedback settings-feedback-success" role="status">{successMessage}</div>}

            {savedSettings && (
                <form
                    className="settings-form"
                    onSubmit={(event) => {
                        event.preventDefault();
                        void handleSave();
                    }}
                >
                    <div className="settings-tabs" role="tablist" aria-label="Settings categories">
                        {SETTINGS_TABS.map((tab) => (
                            <button
                                key={tab.id}
                                id={`settings-tab-${tab.id}`}
                                type="button"
                                className={`settings-tab${activeTab === tab.id ? ' settings-tab-active' : ''}`}
                                role="tab"
                                aria-selected={activeTab === tab.id}
                                aria-controls={`settings-panel-${tab.id}`}
                                tabIndex={activeTab === tab.id ? 0 : -1}
                                onClick={() => setActiveTab(tab.id)}
                                disabled={isBusy}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {activeTab === 'roulette' && (
                        <section
                            id="settings-panel-roulette"
                            className="settings-panel"
                            role="tabpanel"
                            aria-labelledby="settings-tab-roulette"
                        >
                            <div className="settings-section-header">
                                <div>
                                    <p className="page-eyebrow">Outcome pool</p>
                                    <h2>Roulette numbers</h2>
                                </div>
                                <p>Limit the outcomes available to generated roulette data and accepted live observations.</p>
                            </div>

                            <div className="settings-field-row">
                                <div className="settings-field-copy">
                                    <span className="settings-field-title">Selectable number range</span>
                                    <p id="settings-range-help">Choose an inclusive range from 0 to 36. Stored training data outside the range is ignored when a new run starts.</p>
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
                                                    setMinimumNumber(event.target.value);
                                                    clearRangeValidation();
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
                                                    setMaximumNumber(event.target.value);
                                                    clearRangeValidation();
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
                                    <label htmlFor="settings-exclude-zero">Exclude number 0</label>
                                    <p id="settings-exclude-zero-help">Remove zero from generated roulette outcomes and reject zero as a live observation.</p>
                                </div>
                                <div className="settings-field-control">
                                    <label className="settings-checkbox-label" htmlFor="settings-exclude-zero">
                                        <input
                                            id="settings-exclude-zero"
                                            type="checkbox"
                                            checked={excludeZero}
                                            onChange={(event) => {
                                                setExcludeZero(event.target.checked);
                                                setValidationErrors((current) => ({ ...current, rouletteRange: undefined }));
                                            }}
                                            aria-describedby="settings-exclude-zero-help"
                                            disabled={isBusy}
                                        />
                                        <span>{excludeZero ? 'Excluded' : 'Included'}</span>
                                    </label>
                                </div>
                            </div>
                        </section>
                    )}

                    {activeTab === 'appearance' && (
                        <section
                            id="settings-panel-appearance"
                            className="settings-panel"
                            role="tabpanel"
                            aria-labelledby="settings-tab-appearance"
                        >
                            <div className="settings-section-header">
                                <div>
                                    <p className="page-eyebrow">Wheel rendering</p>
                                    <h2>Roulette appearance</h2>
                                </div>
                                <p>Change how newly rendered roulette wheel frames are displayed without changing model color features or reward rules.</p>
                            </div>

                            <div className="settings-field-row settings-checkbox-row">
                                <div className="settings-field-copy">
                                    <label htmlFor="settings-invert-colors">Invert roulette colors</label>
                                    <p id="settings-invert-colors-help">Swap red and black wheel slice colors. Zero remains green.</p>
                                </div>
                                <div className="settings-field-control">
                                    <label className="settings-checkbox-label" htmlFor="settings-invert-colors">
                                        <input
                                            id="settings-invert-colors"
                                            type="checkbox"
                                            checked={invertColors}
                                            onChange={(event) => setInvertColors(event.target.checked)}
                                            aria-describedby="settings-invert-colors-help"
                                            disabled={isBusy}
                                        />
                                        <span>{invertColors ? 'Inverted' : 'Standard'}</span>
                                    </label>
                                </div>
                            </div>

                            <div className="settings-field-row settings-checkbox-row">
                                <div className="settings-field-copy">
                                    <label htmlFor="settings-show-number-labels">Show wheel number labels</label>
                                    <p id="settings-show-number-labels-help">Show or hide number labels on rendered roulette wheel frames.</p>
                                </div>
                                <div className="settings-field-control">
                                    <label className="settings-checkbox-label" htmlFor="settings-show-number-labels">
                                        <input
                                            id="settings-show-number-labels"
                                            type="checkbox"
                                            checked={showNumberLabels}
                                            onChange={(event) => setShowNumberLabels(event.target.checked)}
                                            aria-describedby="settings-show-number-labels-help"
                                            disabled={isBusy}
                                        />
                                        <span>{showNumberLabels ? 'Visible' : 'Hidden'}</span>
                                    </label>
                                </div>
                            </div>
                        </section>
                    )}

                    {activeTab === 'runtime' && (
                        <section
                            id="settings-panel-runtime"
                            className="settings-panel"
                            role="tabpanel"
                            aria-labelledby="settings-tab-runtime"
                        >
                            <div className="settings-section-header">
                                <div>
                                    <p className="page-eyebrow">Runtime</p>
                                    <h2>Training polling</h2>
                                </div>
                                <p>Control how often the parent application polls training progress and status.</p>
                            </div>
                            <div className="settings-field-row">
                                <div className="settings-field-copy">
                                    <label htmlFor="settings-polling-interval">Training polling interval</label>
                                    <p id="settings-polling-help">Future training runs use the saved cadence. A running worker keeps the value captured when it started.</p>
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
                                            setPollingInterval(event.target.value);
                                            setValidationErrors((current) => ({ ...current, pollingInterval: undefined }));
                                        }}
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

                    {activeTab === 'advanced' && (
                        <section
                            id="settings-panel-advanced"
                            className="settings-panel"
                            role="tabpanel"
                            aria-labelledby="settings-tab-advanced"
                        >
                            <div className="settings-section-header">
                                <div>
                                    <p className="page-eyebrow">Training compilation</p>
                                    <h2>JIT model construction</h2>
                                </div>
                                <p>These controls apply when a fresh training model is constructed, not to active or loaded checkpoint models. Saving checks runtime support and never silently falls back.</p>
                            </div>
                            <div className="settings-field-row settings-checkbox-row">
                                <div className="settings-field-copy">
                                    <label htmlFor="settings-jit-compile">Enable JIT compilation</label>
                                    <p id="settings-jit-compile-help">Use the selected compiler backend for newly constructed training models.</p>
                                </div>
                                <div className="settings-field-control">
                                    <label className="settings-checkbox-label" htmlFor="settings-jit-compile">
                                        <input
                                            id="settings-jit-compile"
                                            type="checkbox"
                                            checked={jitCompile}
                                            onChange={(event) => setJitCompile(event.target.checked)}
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
                                    <p id="settings-jit-backend-help">Keep the backend value saved when JIT is disabled; it will be ready if JIT is enabled later.</p>
                                </div>
                                <div className="settings-field-control">
                                    <input
                                        id="settings-jit-backend"
                                        className="settings-input"
                                        type="text"
                                        value={jitBackend}
                                        onChange={(event) => {
                                            setJitBackend(event.target.value);
                                            setValidationErrors((current) => ({ ...current, jitBackend: undefined }));
                                        }}
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

                    <div className="settings-actions">
                        <button type="button" className="settings-button settings-button-secondary" onClick={() => void handleReset()} disabled={isBusy}>
                            {resetting ? 'Resetting…' : 'Reset to defaults'}
                        </button>
                        <button type="submit" className="settings-button settings-button-primary" disabled={isBusy || !isDirty}>
                            {saving ? 'Saving…' : 'Save settings'}
                        </button>
                    </div>
                </form>
            )}
        </div>
    );
};

export default SettingsPage;
