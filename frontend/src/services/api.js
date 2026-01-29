import { API_BASE_URL } from '../config/constants';
import { clearToken, getToken } from './authService';

// URL Base del Backend
const API_URL = API_BASE_URL;

export const authFetch = async (url, options = {}) => {
    const token = getToken();
    const headers = {
        ...(options.headers || {}),
    };
    if (token) headers['Authorization'] = `Token ${token}`;
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
        // Session expired/invalid: force logout.
        clearToken();
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
    }
    return res;
};

export const fetchDashboardStats = async () => {
    try {
        const response = await authFetch(`${API_URL}/dashboard/stats/`);
        if (!response.ok) throw new Error('Network response was not ok');
        return await response.json();
    } catch (error) {
        console.error("Error fetching dashboard stats:", error);
        throw error;
    }
};

export const fetchGoldMine = async (params = {}) => {
    try {
        const query = new URLSearchParams(params).toString();
        const response = await authFetch(`${API_URL}/gold-mine/?${query}`);
        if (!response.ok) throw new Error('Network response was not ok');
        return await response.json();
    } catch (error) {
        console.error("Error fetching gold mine:", error);
        throw error;
    }
};

export const fetchGoldMineStats = async (params = {}) => {
    try {
        const query = new URLSearchParams(params).toString();
        const response = await authFetch(`${API_URL}/gold-mine/stats/?${query}`);
        if (!response.ok) throw new Error('Network response was not ok');
        return await response.json();
    } catch (error) {
        console.error("Error fetching gold mine stats:", error);
        return {};
    }
};

export const searchVisualGoldMine = async (imageFile) => {
    try {
        const formData = new FormData();
        formData.append('image', imageFile);

        const response = await authFetch(`${API_URL}/gold-mine/`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) throw new Error('Network response was not ok');
        return await response.json();
    } catch (error) {
        console.error("Error is visual search:", error);
        throw error;
    }
};

export const fetchCategories = async () => {
    try {
        const response = await authFetch(`${API_URL}/categories/`);
        if (!response.ok) throw new Error('Network response was not ok');
        return await response.json();
    } catch (error) {
        console.error("Error fetching categories:", error);
        return [];
    }
};

export const fetchSystemLogs = async () => {
    try {
        const response = await authFetch(`${API_URL}/system-logs/`);
        if (!response.ok) throw new Error('Network response was not ok');
        return await response.json();
    } catch {
        return []; // Return empty on error to avoid crashing UI
    }
};

export const fetchContainerStats = async () => {
    try {
        const response = await authFetch(`${API_URL}/control/stats/`);
        if (!response.ok) throw new Error('Stats fetch failed');
        return await response.json();
    } catch (error) {
        console.error("Error fetching container stats:", error);
        return {};
    }
};

export const controlContainer = async (service, action) => {
    try {
        const response = await authFetch(`${API_URL}/control/container/${service}/${action}/`, {
            method: 'POST'
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Action failed');
        return data;
    } catch (error) {
        console.error(`Error controlling ${service}:`, error);
        throw error;
    }
};

// -----------------------------
// Dropi Accounts (múltiples cuentas secundarias)
// -----------------------------

export const fetchDropiAccounts = async () => {
    const response = await authFetch(`${API_URL}/dropi/accounts/`, {
        headers: { 'Content-Type': 'application/json' }
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudieron cargar las cuentas Dropi');
    return data.accounts || [];
};

export const createDropiAccount = async ({ label, email, password, is_default }) => {
    const response = await authFetch(`${API_URL}/dropi/accounts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label, email, password, is_default })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo crear la cuenta Dropi');
    return data.account;
};

export const setDefaultDropiAccount = async (accountId) => {
    const response = await authFetch(`${API_URL}/dropi/accounts/${accountId}/default/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'No se pudo marcar como default');
    return true;
};

// -----------------------------
// Reporter Config (schedule time)
// -----------------------------

export const fetchReporterConfig = async () => {
    const response = await authFetch(`${API_URL}/reporter/config/`, {
        headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo cargar la configuración del reporter');
    return data;
};

export const updateReporterConfig = async ({ executionTime }) => {
    const response = await authFetch(`${API_URL}/reporter/config/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ executionTime }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo actualizar la configuración');
    return data;
};

// -----------------------------
// Reporter Control & Status
// -----------------------------

export const startReporterWorkflow = async () => {
    const response = await authFetch(`${API_URL}/reporter/start/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo iniciar el workflow');
    return data;
};

export const fetchReporterStatus = async () => {
    const response = await authFetch(`${API_URL}/reporter/status/`, {
        headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo obtener el estado');
    return data;
};

export const fetchReporterList = async (page = 1, pageSize = 50, statusFilter = 'reportado') => {
    const params = new URLSearchParams({ page: page.toString(), page_size: pageSize.toString() });
    if (statusFilter) params.append('status', statusFilter);
    const response = await authFetch(`${API_URL}/reporter/list/?${params.toString()}`, {
        headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo obtener la lista');
    return data;
};

export const fetchClientDashboardAnalytics = async (period = 'week') => {
    try {
        const params = new URLSearchParams({ period });
        const response = await authFetch(`${API_URL}/user/dashboard/analytics/?${params.toString()}`);
        if (!response.ok) throw new Error('Error al cargar analytics');
        return await response.json();
    } catch (error) {
        console.error('Error fetching client dashboard analytics:', error);
        throw error;
    }
};

// Legacy function (keeping for compatibility)
export const updateReporterConfigLegacy = async ({ executionTime }) => {
    const response = await authFetch(`${API_URL}/reporter/config/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ executionTime }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo guardar la hora de ejecución');
    return data;
};
