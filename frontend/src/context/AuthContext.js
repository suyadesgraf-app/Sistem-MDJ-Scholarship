import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "@/lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null); // null = checking, false = anon, object = user
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      setUser(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    // Only verify session if we have a token (JWT) or are on a protected route
    const hasToken = localStorage.getItem("mdj_token");
    const onProtected = /^\/(dashboard|admin|super-admin)/.test(window.location.pathname);
    if (!hasToken && !onProtected) {
      setUser(false);
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const applyAuth = (data) => {
    if (data.token) localStorage.setItem("mdj_token", data.token);
    setUser(data.user);
    setLoading(false);
  };

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    applyAuth(data);
    return data.user;
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    applyAuth(data);
    return data.user;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem("mdj_token");
    setUser(false);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, checkAuth, applyAuth, setUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

export function dashboardPath(role) {
  if (role === "super_admin") return "/super-admin";
  if (role === "admin") return "/admin";
  return "/dashboard";
}
