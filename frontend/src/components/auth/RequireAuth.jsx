import React, { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getAuthUser, getToken, me } from "../../services/authService";

export default function RequireAuth({ children }) {
  const location = useLocation();
  const token = getToken();
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState(getAuthUser());

  useEffect(() => {
    let mounted = true;
    const refresh = async () => {
      if (!token) {
        if (mounted) setReady(true);
        return;
      }
      try {
        // Always refresh user from backend so tier/active changes apply immediately.
        const u = await me();
        if (mounted) setUser(u);
      } catch {
        // ignore; route will redirect below if user missing
      } finally {
        if (mounted) setReady(true);
      }
    };
    refresh();

    const onFocus = () => {
      // Re-check on tab focus to pick up admin changes quickly.
      setReady(false);
      refresh();
    };
    window.addEventListener("focus", onFocus);

    return () => {
      mounted = false;
      window.removeEventListener("focus", onFocus);
    };
  }, [token]);

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (!ready) return <div style={{ padding: "2rem", color: "#94a3b8" }}>Cargando sesión...</div>;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}

