import { createContext } from 'react';
import type React from 'react';
import type { AppAction, AppState } from './AppStateContext';

export interface AppStateContextType {
    state: AppState;
    dispatch: React.Dispatch<AppAction>;
}

export const AppStateContext = createContext<AppStateContextType | undefined>(undefined);
