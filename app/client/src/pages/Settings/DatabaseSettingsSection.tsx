// Copyright © 2026 Thomas Virdis
// Licensed under the MIT License.

import { useCallback, useEffect, useState } from 'react';
import type {
    DatabaseConfigurationInput,
    DatabaseConfigurationResponse,
    DatabaseStatusResponse,
    SettingsResponse,
} from '../../generated/api';
import { fetchSettings } from '../../utils/settingsApi';
import {
    fetchDatabaseStatus,
    testDatabaseConnection,
    updateDatabaseSettings,
} from '../../utils/databaseSettingsApi';

interface DatabaseSettingsSectionProps {
    hasUnsavedSettings: boolean;
    onSettingsReloaded: (settings: SettingsResponse) => void;
}

const EMPTY_CANDIDATE: DatabaseConfigurationInput = {
    backend: 'sqlite',
    sqlite_path: '',
    host: '',
    port: 5432,
    database_name: '',
    username: '',
    password: '',
    clear_password: false,
    ssl: false,
    ssl_ca: '',
    connect_timeout: 10,
    insert_batch_size: 1000,
};

const fromPublicConfiguration = (
    configuration: DatabaseConfigurationResponse | null,
): DatabaseConfigurationInput => ({
    backend: configuration?.backend ?? 'sqlite',
    sqlite_path: configuration?.sqlite_path ?? '',
    host: configuration?.host ?? '',
    port: configuration?.port ?? 5432,
    database_name: configuration?.database_name ?? '',
    username: configuration?.username ?? '',
    password: '',
    clear_password: false,
    ssl: configuration?.ssl ?? false,
    ssl_ca: configuration?.ssl_ca ?? '',
    connect_timeout: configuration?.connect_timeout ?? 10,
    insert_batch_size: configuration?.insert_batch_size ?? 1000,
});

const DatabaseSettingsSection: React.FC<DatabaseSettingsSectionProps> = ({
    hasUnsavedSettings,
    onSettingsReloaded,
}) => {
    const [status, setStatus] = useState<DatabaseStatusResponse | null>(null);
    const [draft, setDraft] = useState<DatabaseConfigurationInput>(EMPTY_CANDIDATE);
    const [loading, setLoading] = useState(true);
    const [testing, setTesting] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState<string | null>(null);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

    const synchronizeStatus = useCallback((nextStatus: DatabaseStatusResponse) => {
        setStatus(nextStatus);
        setDraft(fromPublicConfiguration(nextStatus.configuration));
    }, []);

    const loadStatus = useCallback(async (signal?: AbortSignal) => {
        setLoading(true);
        setError(null);
        try {
            const nextStatus = await fetchDatabaseStatus(signal);
            if (!signal?.aborted) synchronizeStatus(nextStatus);
        } catch (requestError) {
            if (!signal?.aborted) {
                setError(requestError instanceof Error ? requestError.message : 'Unable to load database settings.');
            }
        } finally {
            if (!signal?.aborted) setLoading(false);
        }
    }, [synchronizeStatus]);

    useEffect(() => {
        const controller = new AbortController();
        void loadStatus(controller.signal);
        return () => controller.abort();
    }, [loadStatus]);

    const setField = <K extends keyof DatabaseConfigurationInput>(
        field: K,
        value: DatabaseConfigurationInput[K],
    ) => {
        setDraft((current) => ({ ...current, [field]: value }));
        setError(null);
        setNotice(null);
        setTestResult(null);
    };

    const toggleClearPassword = (clearPassword: boolean) => {
        setDraft((current) => ({
            ...current,
            password: clearPassword ? '' : current.password,
            clear_password: clearPassword,
        }));
        setError(null);
        setNotice(null);
        setTestResult(null);
    };

    const runConnectionTest = async () => {
        setTesting(true);
        setError(null);
        setNotice(null);
        setTestResult(null);
        try {
            const result = await testDatabaseConnection(draft);
            setTestResult(result);
        } catch (requestError) {
            setError(requestError instanceof Error ? requestError.message : 'Unable to test the database connection.');
        } finally {
            setTesting(false);
        }
    };

    const applyDatabase = async () => {
        if (hasUnsavedSettings) {
            const confirmed = window.confirm(
                'This database has its own application settings and data. Nothing will be copied. Continue and discard your unsaved Settings changes?',
            );
            if (!confirmed) return;
        }

        setSaving(true);
        setError(null);
        setNotice(null);
        setTestResult(null);
        try {
            const nextStatus = await updateDatabaseSettings(draft);
            synchronizeStatus(nextStatus);
            try {
                const settings = await fetchSettings();
                onSettingsReloaded(settings);
                setNotice('Database activated. Settings were reloaded from that database.');
            } catch {
                setNotice('Database activated, but Settings could not be refreshed. Reload the page to load its settings.');
            }
        } catch (requestError) {
            setError(requestError instanceof Error ? requestError.message : 'Unable to activate the database.');
        } finally {
            setSaving(false);
        }
    };

    const busy = loading || testing || saving;
    const configuredPassword = status?.configuration?.backend === 'postgresql'
        && status.configuration.password_configured;

    return (
        <section
            id="settings-panel-database"
            className="settings-panel database-settings-panel"
            aria-labelledby="settings-nav-database"
        >
            <div className="settings-section-header">
                <div>
                    <h2>Database connection</h2>
                </div>
                <p>Connection details are stored separately. Each database keeps its own application settings and data; switching does not copy anything.</p>
            </div>

            <div className="database-status-row" role="status">
                <span className={`database-status-indicator database-status-indicator--${status?.status ?? 'recovery'}`} aria-hidden="true" />
                <span>
                    {status?.status === 'ready'
                        ? `Active: ${status.active_backend === 'postgresql' ? 'PostgreSQL' : 'SQLite'}`
                        : status?.status === 'testing'
                            ? 'Database switch in progress…'
                            : 'Database recovery required'}
                </span>
                {loading && <span className="database-status-secondary">Checking status…</span>}
            </div>

            {status?.message && (
                <div className="settings-feedback settings-feedback-error" role="alert">{status.message}</div>
            )}
            {error && <div className="settings-feedback settings-feedback-error" role="alert">{error}</div>}
            {notice && <div className="settings-feedback settings-feedback-success" role="status">{notice}</div>}
            {testResult && (
                <div className={`settings-feedback ${testResult.success ? 'settings-feedback-success' : 'settings-feedback-error'}`} role={testResult.success ? 'status' : 'alert'}>
                    {testResult.message}
                </div>
            )}

            <div className="settings-field-row">
                <div className="settings-field-copy">
                    <label htmlFor="database-backend">Backend</label>
                    <p>SQLite stores data in a local file. PostgreSQL uses the postgresql+psycopg driver.</p>
                </div>
                <div className="settings-field-control">
                    <select
                        id="database-backend"
                        className="settings-input"
                        value={draft.backend}
                        onChange={(event) => setField('backend', event.target.value as DatabaseConfigurationInput['backend'])}
                        disabled={busy}
                    >
                        <option value="sqlite">SQLite</option>
                        <option value="postgresql">PostgreSQL</option>
                    </select>
                </div>
            </div>

            {draft.backend === 'sqlite' ? (
                <div className="settings-field-row">
                    <div className="settings-field-copy">
                        <label htmlFor="database-sqlite-path">Database file</label>
                        <p>Choose the SQLite file to use. The default is the database.db file in the data directory.</p>
                    </div>
                    <div className="settings-field-control">
                        <input
                            id="database-sqlite-path"
                            className="settings-input"
                            type="text"
                            value={draft.sqlite_path ?? ''}
                            onChange={(event) => setField('sqlite_path', event.target.value)}
                            autoComplete="off"
                            disabled={busy}
                        />
                    </div>
                </div>
            ) : (
                <>
                    <div className="settings-field-row">
                        <div className="settings-field-copy">
                            <label htmlFor="database-host">Host and port</label>
                            <p>Enter the PostgreSQL server address and port.</p>
                        </div>
                        <div className="database-field-pair">
                            <input id="database-host" className="settings-input" type="text" value={draft.host ?? ''} onChange={(event) => setField('host', event.target.value)} autoComplete="off" disabled={busy} aria-label="PostgreSQL host" />
                            <input id="database-port" className="settings-input" type="number" min="1" max="65535" value={draft.port ?? 5432} onChange={(event) => setField('port', Number(event.target.value))} disabled={busy} aria-label="PostgreSQL port" />
                        </div>
                    </div>
                    <div className="settings-field-row">
                        <div className="settings-field-copy">
                            <label htmlFor="database-name">Database and username</label>
                        </div>
                        <div className="database-field-pair">
                            <input id="database-name" className="settings-input" type="text" value={draft.database_name ?? ''} onChange={(event) => setField('database_name', event.target.value)} autoComplete="off" disabled={busy} aria-label="PostgreSQL database name" />
                            <input id="database-username" className="settings-input" type="text" value={draft.username ?? ''} onChange={(event) => setField('username', event.target.value)} autoComplete="username" disabled={busy} aria-label="PostgreSQL username" />
                        </div>
                    </div>
                    <div className="settings-field-row">
                        <div className="settings-field-copy">
                            <label htmlFor="database-password">Password</label>
                            <p>{configuredPassword ? 'A password is saved securely. Leave this blank to keep it.' : 'Password is optional when the server uses another authentication method.'}</p>
                        </div>
                        <div className="settings-field-control">
                            <input id="database-password" className="settings-input" type="password" value={draft.password ?? ''} onChange={(event) => setField('password', event.target.value)} autoComplete="new-password" placeholder={configuredPassword ? 'Saved password (leave blank to keep)' : 'Password'} disabled={busy || draft.clear_password} />
                            {configuredPassword && (
                                <label className="settings-checkbox-label" htmlFor="database-clear-password">
                                    <input id="database-clear-password" type="checkbox" checked={Boolean(draft.clear_password)} onChange={(event) => toggleClearPassword(event.target.checked)} disabled={busy} />
                                    <span>Clear saved password</span>
                                </label>
                            )}
                        </div>
                    </div>
                    <div className="settings-field-row">
                        <div className="settings-field-copy">
                            <label htmlFor="database-ssl-ca">SSL and CA certificate</label>
                            <p>Enable SSL verification requirements and optionally provide a CA certificate path.</p>
                        </div>
                        <div className="settings-field-control">
                            <label className="settings-checkbox-label" htmlFor="database-ssl">
                                <input id="database-ssl" type="checkbox" checked={Boolean(draft.ssl)} onChange={(event) => setField('ssl', event.target.checked)} disabled={busy} />
                                <span>Require SSL</span>
                            </label>
                            <input id="database-ssl-ca" className="settings-input" type="text" value={draft.ssl_ca ?? ''} onChange={(event) => setField('ssl_ca', event.target.value)} placeholder="Optional CA certificate path" autoComplete="off" disabled={busy || !draft.ssl} />
                        </div>
                    </div>
                </>
            )}

            <div className="settings-field-row">
                <div className="settings-field-copy">
                    <label htmlFor="database-connect-timeout">Connection timeout</label>
                    <p>Maximum seconds to wait for a PostgreSQL connection.</p>
                </div>
                <div className="settings-field-control settings-number-control">
                    <input id="database-connect-timeout" className="settings-input" type="number" min="1" max="300" value={draft.connect_timeout ?? 10} onChange={(event) => setField('connect_timeout', Number(event.target.value))} disabled={busy || draft.backend === 'sqlite'} />
                    <span>seconds</span>
                </div>
            </div>
            <div className="settings-field-row">
                <div className="settings-field-copy">
                    <label htmlFor="database-batch-size">Insert batch size</label>
                    <p>Maximum rows written in one dataset import batch.</p>
                </div>
                <div className="settings-field-control settings-number-control">
                    <input id="database-batch-size" className="settings-input" type="number" min="1" max="100000" value={draft.insert_batch_size ?? 1000} onChange={(event) => setField('insert_batch_size', Number(event.target.value))} disabled={busy} />
                    <span>rows</span>
                </div>
            </div>

            <div className="settings-actions database-settings-actions">
                <button type="button" className="settings-button settings-button-secondary" onClick={() => void runConnectionTest()} disabled={busy}>
                    {testing ? 'Testing…' : 'Test connection'}
                </button>
                <button type="button" className="settings-button settings-button-primary" onClick={() => void applyDatabase()} disabled={busy}>
                    {saving ? 'Applying…' : 'Apply and switch'}
                </button>
            </div>
        </section>
    );
};

export default DatabaseSettingsSection;
