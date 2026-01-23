import { API_BASE_URL } from "../config/constants";
import { authFetch } from "./api";

const API_URL = API_BASE_URL;

export async function fetchAdminUsers() {
  const res = await authFetch(`${API_URL}/admin/users/`, {
    headers: { "Content-Type": "application/json" },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "No se pudieron cargar usuarios");
  return data.users || [];
}

export async function setUserSubscription(userId, { subscription_tier, subscription_active }) {
  const res = await authFetch(`${API_URL}/admin/users/${userId}/subscription/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subscription_tier, subscription_active }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "No se pudo actualizar suscripción");
  return data;
}

