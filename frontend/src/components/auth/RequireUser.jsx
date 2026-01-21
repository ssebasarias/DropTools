import React from "react";
import { Navigate } from "react-router-dom";
import { getAuthUser } from "../../services/authService";

export default function RequireUser({ children }) {
  const user = getAuthUser();
  if (!user) return <Navigate to="/login" replace />;
  if (user.is_admin) return <Navigate to="/admin" replace />;
  return children;
}

