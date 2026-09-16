import { useCallback, useEffect, useMemo, useState } from 'react';
import type { SettingsPatchRequest, SettingsResponse } from '../../generated/api';
import { isAbortError } from '../../utils/apiClient';
import { fetchSettings, resetSettings, updateSettings } from '../../utils/settingsApi';
import './SettingsPage.css';

interface ValidationErrors {
    pollingInterval?: string;
    jitBackend?: string;
}

const SETTINGS_ERROR = 'Unable to load settings.';

const SettingsPage: React.FC = () => {
    const [savedSettings, setSavedSettings] = useState<SettingsResponse | null>(null);
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
            return { polling: false, jitCompile: false, jitBackend: false };
        }
        return {
            polling: Number(pollingInterval) !== savedSettings.jobs.polling_interval,
            jitCompile: jitCompile !== savedSettings.device.jit_compile,
            jitBackend: jitBackend.trim() !== savedSettings.device.jit_backend,
        };
    }, [jitBackend, jitCompile, pollingInterval, savedSettings]);

    const isDirty = dirtyFields.polling || dirtyFields.jitCompile || dirtyFields.jitBackend;
    const isBusy = loading || saving || resetting;

    const validateDraft = (): ValidationErrors => {
        const nextErrors: ValidationErrors = {};
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
        return nextErrors;
    };

    const handleSave = async () => {
        setError(null);
        setSuccessMessage(null);
        const nextErrors = validateDraft();
        if (Object.keys(nextErrors).length > 0 || !savedSettings || !isDirty) {
            return;
        }

        const patch: SettingsPatchRequest = {};
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
                    Adjust application-wide training runtime behavior. Environment and per-training settings remain managed in their own files and workflows.
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
                    <section className="settings-section" aria-labelledby="settings-runtime-heading">
                        <div className="settings-section-header">
                            <div>
                                <p className="page-eyebrow">Runtime</p>
                                <h2 id="settings-runtime-heading">Training polling</h2>
                            </div>
                            <p>Control how often the parent application polls training progress and status.</p>
                        </div>
                        <div className="settings-field-row">
                            <div className="settings-field-copy">
                                <label htmlFor="settings-polling-interval">Training polling interval</label>
                                <p id="settings-polling-help">
                                    Future training runs use the saved cadence. A running worker keeps the value captured when it started.
                                </p>
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

                    <section className="settings-section" aria-labelledby="settings-device-heading">
                        <div className="settings-section-header">
                            <div>
                                <p className="page-eyebrow">Training compilation</p>
                                <h2 id="settings-device-heading">JIT model construction</h2>
                            </div>
                            <p>These controls apply when a fresh training model is constructed, not to active or loaded checkpoint models.</p>
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
