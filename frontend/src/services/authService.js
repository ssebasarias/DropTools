import { API_BASE_URL } from "../config/constants";

const API_URL = API_BASE_URL;

export function getToken() {
  const local = localStorage.getItem("auth_token");
  if (local) return local;
  const legacy = sessionStorage.getItem("auth_token");
  if (legacy) {
    localStorage.setItem("auth_token", legacy);
    sessionStorage.removeItem("auth_token");
    return legacy;
  }
  return null;
}

export function setToken(token) {
  localStorage.setItem("auth_token", token);
}

export function clearToken() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_user");
  sessionStorage.removeItem("auth_token");
  sessionStorage.removeItem("auth_user");
}

export function logout() {
  clearToken();
  window.location.replace("/login");
}

export function getAuthUser() {
  const raw = localStorage.getItem("auth_user") || sessionStorage.getItem("auth_user");
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    localStorage.setItem("auth_user", raw);
    sessionStorage.removeItem("auth_user");
    return parsed;
  } catch {
    clearToken();
    return null;
  }
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
  if (!res.ok) throw new Error(data.error || data.detail || "Registro falló");
  return data;
}

export async function verifyEmail(token) {
  const res = await fetch(`${API_URL}/auth/verify-email/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "No se pudo verificar el email");
  return data;
}

export async function passwordResetRequest(email) {
  const res = await fetch(`${API_URL}/auth/password-reset/request/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "No se pudo procesar la solicitud");
  return data;
}

export async function passwordResetConfirm(token, new_password) {
  const res = await fetch(`${API_URL}/auth/password-reset/confirm/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "No se pudo actualizar la contraseña");
  return data;
}

/**
 * Autenticar con Google OAuth
 * @param {string} googleToken - Token de ID de Google
 * @returns {Promise<{user: Object, token: string}>}
 */
export async function loginWithGoogle(googleToken) {
  try {
    const response = await fetch(`${API_URL}/auth/google/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token: googleToken }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const msg = typeof data.error === 'string' ? data.error : (data.error?.message || JSON.stringify(data.error) || 'Error al autenticar con Google');
      throw new Error(msg);
    }

    // Guardar token y usuario en localStorage para persistir entre sesiones.
    setToken(data.token);
    localStorage.setItem("auth_user", JSON.stringify(data.user));
    
    return data;
  } catch (error) {
    console.error('Error en loginWithGoogle:', error);
    throw error;
  }
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

