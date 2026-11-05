// Copyright © 2023 Thomas Virdis
// Licensed under the MIT License.

import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/Layout/MainLayout';
import { GuidanceProvider } from './components/guidance/GuidanceProvider';
import StartupScreen from './components/startup/StartupScreen';
import { useBackendStartup } from './hooks/useBackendStartup';
import './styles/global.css';

const TrainingPage = lazy(() => import('./pages/Training/TrainingPage'));
const InferencePage = lazy(() => import('./pages/Inference/InferencePage'));
const SettingsPage = lazy(() => import('./pages/Settings/SettingsPage'));

function AppRoutes({ databaseRecovery = false }: { databaseRecovery?: boolean }) {
    return (
        <BrowserRouter>
            <GuidanceProvider>
                <div className="app-ready-transition">
                    <Suspense fallback={null}>
                    <Routes>
                        <Route path="/" element={<MainLayout />}>
                            <Route index element={<Navigate to={databaseRecovery ? '/settings?section=database' : '/training'} replace />} />
                            <Route path="training" element={<TrainingPage />} />
                            <Route path="inference" element={<InferencePage />} />
                            <Route path="settings" element={<SettingsPage />} />
                        </Route>
                    </Routes>
                    </Suspense>
                </div>
            </GuidanceProvider>
        </BrowserRouter>
    );
}

function App() {
    const startup = useBackendStartup();

    if (startup.status === 'waiting' || startup.status === 'error') {
        return (
            <StartupScreen
                status={startup.status}
                elapsedSeconds={startup.elapsedSeconds}
                onRetry={startup.retry}
            />
        );
    }

    return <AppRoutes databaseRecovery={startup.status === 'recovery'} />;
}

export default App;
