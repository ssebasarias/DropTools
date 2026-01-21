import React from "react";
import { Navigate } from "react-router-dom";
import { getAuthUser } from "../../services/authService";

export default function RequireAdmin({ children }) {
  const user = getAuthUser();
  if (!user) return <Navigate to="/login" replace />;
  if (!user.is_admin) return <Navigate to="/user/reporter-setup" replace />;
  return children;
}

