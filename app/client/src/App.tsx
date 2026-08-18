import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppStateProvider } from './context/AppStateContext';
import MainLayout from './components/Layout/MainLayout';
import TrainingPage from './pages/Training/TrainingPage';
import InferencePage from './pages/Inference/InferencePage';
import { GuidanceProvider } from './components/guidance/GuidanceProvider';
import './styles/global.css';

function App() {
  return (
    <AppStateProvider>
      <BrowserRouter>
        <GuidanceProvider>
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Navigate to="/training" replace />} />
              <Route path="training" element={<TrainingPage />} />
              <Route path="inference" element={<InferencePage />} />
            </Route>
          </Routes>
        </GuidanceProvider>
      </BrowserRouter>
    </AppStateProvider>
  );
}

export default App;
