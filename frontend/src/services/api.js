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

/** Timeout para POST reporter/start: en desarrollo puede tardar 1-2 min (ejecución en proceso) */
const REPORTER_START_TIMEOUT_MS = 120000;

export const startReporterWorkflow = async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REPORTER_START_TIMEOUT_MS);
    try {
        const response = await authFetch(`${API_URL}/reporter/start/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const err = new Error(data.error || 'No se pudo iniciar el workflow');
            err.body = data;
            throw err;
        }
        return data;
    } finally {
        clearTimeout(timeoutId);
    }
};

/** Modo activo (desarrollo vs producción). Público, no requiere auth. */
export const fetchReporterEnv = async () => {
    const response = await fetch(`${API_URL}/reporter/env/`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) return { droptools_env: 'production', reporter_use_celery: true };
    return data;
};

/** Detener todos los procesos del reporter (Celery activos + cola). Solo en modo desarrollo. */
export const stopReporterProcesses = async () => {
    const response = await authFetch(`${API_URL}/reporter/stop/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const err = new Error(data.error || 'No se pudieron detener los procesos');
        err.body = data;
        throw err;
    }
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

// Reporter slots & reservations (nuevo sistema por hora)
export const fetchReporterSlots = async () => {
    const response = await authFetch(`${API_URL}/reporter/slots/`);
    if (!response.ok) {
        let msg = 'No se pudieron cargar los horarios';
        try {
            const data = await response.json().catch(() => ({}));
            if (data?.error) {
                msg = data.error;
                if (data?.hint) msg += ` — ${data.hint}`;
            } else if (response.status === 401) msg = 'Sesión expirada. Vuelve a iniciar sesión.';
            else if (response.status >= 500) msg = 'Error en el servidor. Revisa que el backend esté en marcha y que hayas ejecutado: python manage.py migrate';
        } catch (_) {}
        throw new Error(msg);
    }
    return await response.json();
};

export const fetchMyReservation = async () => {
    const response = await authFetch(`${API_URL}/reporter/reservations/`);
    if (!response.ok) throw new Error('No se pudo cargar tu reserva');
    const data = await response.json();
    if (data && data.reservation !== undefined) return data.reservation;
    return data && (data.slot_id !== undefined || data.slot) ? data : null;
};

export const createReservation = async ({ slot_id, monthly_orders_estimate }) => {
    const response = await authFetch(`${API_URL}/reporter/reservations/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot_id, monthly_orders_estimate: monthly_orders_estimate || 0 }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo crear la reserva');
    return data;
};

export const deleteReservation = async () => {
    const response = await authFetch(`${API_URL}/reporter/reservations/`, {
        method: 'DELETE',
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'No se pudo cancelar la reserva');
    return data;
};

export const fetchReporterRuns = async (days = 7) => {
    const response = await authFetch(`${API_URL}/reporter/runs/?days=${days}`);
    if (!response.ok) throw new Error('No se pudieron cargar las ejecuciones');
    return await response.json();
};

export const fetchReporterRunProgress = async (runId) => {
    const response = await authFetch(`${API_URL}/reporter/runs/${runId}/progress/`);
    if (!response.ok) throw new Error('No se pudo cargar el progreso');
    return await response.json();
};

export const fetchClientDashboardAnalytics = async (period = 'month') => {
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

export const fetchAnalyticsHistorical = async (startDate, endDate, granularity = 'day') => {
    try {
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate,
            granularity,
        });
        const response = await authFetch(`${API_URL}/user/analytics/historical/?${params.toString()}`);
        if (!response.ok) throw new Error('Error al cargar datos históricos');
        return await response.json();
    } catch (error) {
        console.error('Error fetching analytics historical:', error);
        throw error;
    }
};

export const fetchCarrierComparison = async (period = 'month') => {
    try {
        const params = new URLSearchParams({ period });
        const response = await authFetch(`${API_URL}/user/analytics/carrier-comparison/?${params.toString()}`);
        if (!response.ok) throw new Error('Error al cargar comparativa de transportadoras');
        return await response.json();
    } catch (error) {
        console.error('Error fetching carrier comparison:', error);
        throw error;
    }
};

export const exportAnalyticsReport = async (period, format = 'csv') => {
    try {
        // Esta función puede implementarse más adelante para exportar a Excel/CSV
        const params = new URLSearchParams({ period, format });
        const response = await authFetch(`${API_URL}/user/dashboard/analytics/?${params.toString()}`);
        if (!response.ok) throw new Error('Error al exportar reporte');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analytics-${period}-${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        console.error('Error exporting analytics report:', error);
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
