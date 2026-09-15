import React, { useEffect, useRef } from "react";
import { useLocation, useNavigate, Navigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth, dashboardPath } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";

export const LoadingScreen = ({ label = "Memuat..." }) => (
  <div className="min-h-screen flex flex-col items-center justify-center bg-[#F9FAFB] gap-3">
    <Loader2 className="w-8 h-8 text-[#27AE60] animate-spin" />
    <p className="text-sm text-[#6B7280]">{label}</p>
  </div>
);

export const ProtectedRoute = ({ children, roles }) => {
  const { user, loading } = useAuth();
  if (loading || user === null) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={dashboardPath(user.role)} replace />;
  return children;
};

export const AuthCallback = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { applyAuth } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const hash = location.hash;
    const match = hash.match(/session_id=([^&]+)/);
    if (!match) { navigate("/login", { replace: true }); return; }
    const sessionId = match[1];
    (async () => {
      try {
        const { data } = await api.post("/auth/google/session", { session_id: sessionId });
        applyAuth(data);
        window.history.replaceState(null, "", window.location.pathname);
        navigate(dashboardPath(data.user.role), { replace: true });
      } catch {
        navigate("/login", { replace: true });
      }
    })();
  }, [location, navigate, applyAuth]);

  return <LoadingScreen label="Menyelesaikan proses masuk..." />;
};
