import { Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import Overview from './pages/Overview';
import TextSearch from './pages/TextSearch';
import VisualSearch from './pages/VisualSearch';
import SimilarImages from './pages/SimilarImages';
import ModelComparison from './pages/ModelComparison';
import DatasetExplorer from './pages/DatasetExplorer';
import Evaluation from './pages/Evaluation';
import Architecture from './pages/Architecture';
import ApiDocs from './pages/ApiDocs';
import Settings from './pages/Settings';
import MirflickrSimilar from './pages/MirflickrSimilar';

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/text" element={<TextSearch />} />
        <Route path="/visual" element={<VisualSearch />} />
        <Route path="/similar" element={<SimilarImages />} />
        <Route path="/similar/:path" element={<SimilarImages />} />
        <Route path="/compare" element={<ModelComparison />} />
        <Route path="/dataset" element={<DatasetExplorer />} />
        <Route path="/evaluation" element={<Evaluation />} />
        <Route path="/architecture" element={<Architecture />} />
        <Route path="/api" element={<ApiDocs />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/mirflickr/:photoId" element={<MirflickrSimilar />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
