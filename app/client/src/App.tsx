// Copyright © 2023 Thomas Virdis
// Licensed under the MIT License.

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/Layout/MainLayout';
import TrainingPage from './pages/Training/TrainingPage';
import InferencePage from './pages/Inference/InferencePage';
import SettingsPage from './pages/Settings/SettingsPage';
import { GuidanceProvider } from './components/guidance/GuidanceProvider';
import StartupScreen from './components/startup/StartupScreen';
import { useBackendStartup } from './hooks/useBackendStartup';
import './styles/global.css';

function AppRoutes({ databaseRecovery = false }: { databaseRecovery?: boolean }) {
    return (
        <BrowserRouter>
            <GuidanceProvider>
                <div className="app-ready-transition">
                    <Routes>
                        <Route path="/" element={<MainLayout />}>
                            <Route index element={<Navigate to={databaseRecovery ? '/settings?section=database' : '/training'} replace />} />
                            <Route path="training" element={<TrainingPage />} />
                            <Route path="inference" element={<InferencePage />} />
                            <Route path="settings" element={<SettingsPage />} />
                        </Route>
                    </Routes>
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
