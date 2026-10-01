// Copyright © 2023 Thomas Virdis
// Licensed under the MIT License.

export type BackendStartupStatus = 'waiting' | 'ready' | 'error';

export interface BackendStartupState {
    status: BackendStartupStatus;
    elapsedSeconds: number;
}
