export type BackendStartupStatus = 'waiting' | 'ready' | 'error';

export interface BackendStartupState {
    status: BackendStartupStatus;
    elapsedSeconds: number;
}
