import type {
    SettingsPatchRequest,
    SettingsResponse,
} from '../generated/api';
import { requestJson, requestReadOnlyJson } from './apiClient';

export const fetchSettings = async (
    signal?: AbortSignal,
): Promise<SettingsResponse> => (
    requestReadOnlyJson<SettingsResponse>(
        '/api/settings',
        { signal },
        'Unable to load settings.',
    )
);

export const updateSettings = async (
    patch: SettingsPatchRequest,
    signal?: AbortSignal,
): Promise<SettingsResponse> => (
    requestJson<SettingsResponse>(
        '/api/settings',
        {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(patch),
            signal,
        },
        'Unable to save settings.',
    )
);

export const resetSettings = async (
    signal?: AbortSignal,
): Promise<SettingsResponse> => (
    requestJson<SettingsResponse>(
        '/api/settings/reset',
        { method: 'POST', signal },
        'Unable to reset settings.',
    )
);
