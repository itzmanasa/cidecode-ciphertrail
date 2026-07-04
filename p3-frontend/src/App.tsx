import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { UploadPage } from "./pages/UploadPage";
import { DashboardPage } from "./pages/DashboardPage";
import { MoneyFlowPage } from "./pages/MoneyFlowPage";
import { RoundTrippingPage } from "./pages/RoundTrippingPage";
import { FindingsPage } from "./pages/FindingsPage";
import { TransactionsPage } from "./pages/TransactionsPage";
import { EvidenceReportPage } from "./pages/EvidenceReportPage";
import { CasesPage } from "./pages/CasesPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { MoneyTrailPage } from "./pages/MoneyTrailPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/upload"
          element={
            <ProtectedRoute>
              <UploadPage />
            </ProtectedRoute>
          }
        />
        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/upload" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/money-flow" element={<MoneyFlowPage />} />
          <Route path="/round-tripping" element={<RoundTrippingPage />} />
          <Route path="/findings" element={<FindingsPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/evidence-report" element={<EvidenceReportPage />} />
          <Route path="/cases" element={<CasesPage />} />
          <Route path="/money-trail" element={<MoneyTrailPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/upload" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
