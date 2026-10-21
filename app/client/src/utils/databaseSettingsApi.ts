// Copyright © 2026 Thomas Virdis
// Licensed under the MIT License.

import type {
    DatabaseConfigurationInput,
    DatabaseStatusResponse,
    DatabaseTestResponse,
} from '../generated/api';
import { requestJson, requestReadOnlyJson } from './apiClient';

export const fetchDatabaseStatus = async (
    signal?: AbortSignal,
): Promise<DatabaseStatusResponse> => requestReadOnlyJson<DatabaseStatusResponse>(
    '/api/settings/database',
    { signal },
    'Unable to load database settings.',
);

export const testDatabaseConnection = async (
    candidate: DatabaseConfigurationInput,
): Promise<DatabaseTestResponse> => requestJson<DatabaseTestResponse>(
    '/api/settings/database/test',
    {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(candidate),
    },
    'Unable to test the database connection.',
);

export const updateDatabaseSettings = async (
    candidate: DatabaseConfigurationInput,
): Promise<DatabaseStatusResponse> => requestJson<DatabaseStatusResponse>(
    '/api/settings/database',
    {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(candidate),
    },
    'Unable to activate the database.',
);
