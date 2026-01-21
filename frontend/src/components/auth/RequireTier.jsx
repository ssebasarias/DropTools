import React from "react";
import { Navigate } from "react-router-dom";
import { getAuthUser } from "../../services/authService";
import { hasTier } from "../../utils/subscription";

export default function RequireTier({ minTier = "BRONZE", children }) {
  const user = getAuthUser();
  if (!user) return <Navigate to="/login" replace />;
  if (user.is_admin) return <Navigate to="/admin" replace />;
  if (!hasTier(user, minTier)) return <Navigate to="/user/subscriptions" replace />;
  return children;
}

