import { API_BASE_URL } from "../config/constants";

const API_URL = API_BASE_URL;

export function getToken() {
  return sessionStorage.getItem("auth_token");
}

export function setToken(token) {
  sessionStorage.setItem("auth_token", token);
}

export function clearToken() {
  sessionStorage.removeItem("auth_token");
  sessionStorage.removeItem("auth_user");
}

export function logout() {
  clearToken();
  window.location.href = "/login";
}

export function getAuthUser() {
  const raw = sessionStorage.getItem("auth_user");
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
  sessionStorage.setItem("auth_user", JSON.stringify(data.user));
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
  sessionStorage.setItem("auth_user", JSON.stringify(data.user));
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

    // Guardar token y usuario en sessionStorage (consistente con el resto de la app)
    setToken(data.token);
    sessionStorage.setItem("auth_user", JSON.stringify(data.user));
    
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
  sessionStorage.setItem("auth_user", JSON.stringify(data.user));
  return data.user;
}

