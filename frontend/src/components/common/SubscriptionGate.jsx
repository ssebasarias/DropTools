import React from "react";
import { NavLink } from "react-router-dom";
import { getAuthUser } from "../../services/authService";
import { hasTier } from "../../utils/subscription";

export default function SubscriptionGate({ minTier = "BRONZE", title, children }) {
  const user = getAuthUser();
  const ok = hasTier(user, minTier);

  if (ok) return children;

  return (
    <div style={{ padding: "2rem" }}>
      <div className="glass-card" style={{ padding: "1.5rem" }}>
        <h2 style={{ marginTop: 0 }}>{title || "Funcionalidad bloqueada"}</h2>
        <p className="text-muted" style={{ marginBottom: "1.25rem" }}>
          Tu plan actual ({user?.subscription_tier || "N/A"}) no incluye este módulo. Necesitas al menos{" "}
          <strong>{minTier}</strong>.
        </p>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <NavLink to="/user/subscriptions" className="btn-primary" style={{ textDecoration: "none" }}>
            Ver planes
          </NavLink>
          <NavLink to="/user/reporter-setup" className="btn-secondary" style={{ textDecoration: "none" }}>
            Ir a Reporter
          </NavLink>
        </div>
      </div>
    </div>
  );
}

