import { API_BASE_URL } from "../config/constants";

const API_URL = API_BASE_URL;

export function getToken() {
  return localStorage.getItem("auth_token");
}

export function setToken(token) {
  localStorage.setItem("auth_token", token);
}

export function clearToken() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_user");
}

export function logout() {
  clearToken();
  window.location.href = "/login";
}

export function getAuthUser() {
  const raw = localStorage.getItem("auth_user");
  return raw ? JSON.parse(raw) : null;
}

export async function login(email, password) {
  const res = await fetch(`${API_URL}/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || "Login falló");
  }

  setToken(data.token);
  localStorage.setItem("auth_user", JSON.stringify(data.user));
  return data;
}

export async function register({ full_name, name, email, password }) {
  const res = await fetch(`${API_URL}/auth/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name: full_name || name || "", email, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Registro falló");
  setToken(data.token);
  localStorage.setItem("auth_user", JSON.stringify(data.user));
  return data;
}

export async function me() {
  const token = getToken();
  if (!token) throw new Error("Sin token");
  const res = await fetch(`${API_URL}/auth/me/`, {
    headers: {
      Authorization: `Token ${token}`,
      "Content-Type": "application/json",
    },
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    clearToken();
    throw new Error("Sesión expirada");
  }
  if (!res.ok) throw new Error(data.error || "No se pudo cargar el usuario");
  localStorage.setItem("auth_user", JSON.stringify(data.user));
  return data.user;
}

