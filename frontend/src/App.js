import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute, AuthCallback } from "@/components/Protected";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import StudentDashboard from "@/pages/student/StudentDashboard";
import AdminDashboard from "@/pages/admin/AdminDashboard";
import SuperAdminDashboard from "@/pages/superadmin/SuperAdminDashboard";
import VerifyEmail from "@/pages/VerifyEmail";
import ResetPassword from "@/pages/ResetPassword";
import LegalInformationPage from "@/pages/LegalInformationPage";
import NewsPage from "@/pages/NewsPage";

function AppRoutes() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/privacy-policy" element={<LegalInformationPage pageKey="privacy" />} />
      <Route path="/syarat-ketentuan" element={<LegalInformationPage pageKey="terms" />} />
      <Route path="/pedoman-program" element={<LegalInformationPage pageKey="guide" />} />
      <Route path="/berita" element={<NewsPage />} />
      <Route path="/dashboard" element={<ProtectedRoute roles={["student"]}><StudentDashboard /></ProtectedRoute>} />
      <Route
        path="/admin"
        element={(
          <ProtectedRoute roles={["admin", "admin_wilayah", "super_admin"]}>
            <AdminDashboard />
          </ProtectedRoute>
        )}
      />
      <Route path="/super-admin" element={<ProtectedRoute roles={["super_admin"]}><SuperAdminDashboard /></ProtectedRoute>} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Toaster position="top-center" richColors closeButton />
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
