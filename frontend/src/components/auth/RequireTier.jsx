import React from "react";
import { Navigate } from "react-router-dom";
import { getAuthUser, getToken } from "../../services/authService";
import { hasTier } from "../../utils/subscription";

export default function RequireTier({ minTier = "BRONZE", fallbackPath = "/user/subscriptions", children }) {
  const token = getToken();
  const user = getAuthUser();
  if (!token || !user) return <Navigate to="/login" replace />;
  if (user.is_admin) return <Navigate to="/admin" replace />;
  if (!hasTier(user, minTier)) return <Navigate to={fallbackPath} replace />;
  return children;
}

