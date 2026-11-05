import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from './pages/LoginPage';
import { VendorOnboardingPage } from './pages/VendorOnboardingPage';
import { AdminPlaceholderPage } from './pages/AdminPlaceholderPage';
import { SubmissionSuccessPage } from './pages/SubmissionSuccessPage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/vendor" element={<VendorOnboardingPage />} />
        <Route path="/admin" element={<AdminPlaceholderPage />} />
        <Route path="/submission-success" element={<SubmissionSuccessPage />} />
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
