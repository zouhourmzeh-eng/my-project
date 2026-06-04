import { useEffect } from "react";
import { Route, Routes, Navigate, Outlet } from "react-router-dom";
import Layout from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProcessDetailPage from "./pages/ProcessDetailPage";
import DocumentDetailPage from "./pages/DocumentDetailPage";
import SettingsPage from "./pages/SettingsPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import ArchivedProjectsPage from "./pages/ArchivedProjectsPage";
import RegulatoryHistoryPage from "./pages/RegulatoryHistoryPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";

export default function App() {
  useEffect(() => {
    console.log("QMS Platform Active");
  }, []);

  return (
    <Routes>
      {/* Public Routes — no layout wrapper needed */}
      <Route path="/" element={<LoginPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      {/* Protected Routes — Layout with header/nav */}
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:id" element={<ProjectDetailPage />} />
          <Route path="/processes/:id" element={<ProcessDetailPage />} />
          <Route path="/documents/:id" element={<DocumentDetailPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      {/* Consultant-only Routes */}
      <Route element={<ProtectedRoute roles={["consultant"]} />}>
        <Route element={<Layout />}>
          <Route path="/archived" element={<ArchivedProjectsPage />} />
          <Route path="/regulatory-watch" element={<RegulatoryHistoryPage />} />
        </Route>
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
