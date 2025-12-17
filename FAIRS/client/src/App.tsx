import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/Layout/MainLayout';
import TrainingPage from './pages/Training/TrainingPage';
import InferencePage from './pages/Inference/InferencePage';
import DatabasePage from './pages/Database/DatabasePage';
import './styles/global.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/training" replace />} />
          <Route path="training" element={<TrainingPage />} />
          <Route path="inference" element={<InferencePage />} />
          <Route path="database" element={<DatabasePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
