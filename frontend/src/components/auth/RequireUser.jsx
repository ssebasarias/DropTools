import React from "react";
import { Navigate } from "react-router-dom";
import { getAuthUser, getToken } from "../../services/authService";

export default function RequireUser({ children }) {
  const token = getToken();
  const user = getAuthUser();
  if (!token) return <Navigate to="/login" replace />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.is_admin) return <Navigate to="/admin" replace />;
  return children;
}

