// URL Base del Backend
const API_URL = 'http://localhost:8000/api';

export const fetchDashboardStats = async () => {
    try {
        const response = await fetch(`${API_URL}/dashboard/stats/`);
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
        const response = await fetch(`${API_URL}/gold-mine/?${query}`);
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
        const response = await fetch(`${API_URL}/gold-mine/stats/?${query}`);
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

        const response = await fetch(`${API_URL}/gold-mine/`, {
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
        const response = await fetch(`${API_URL}/categories/`);
        if (!response.ok) throw new Error('Network response was not ok');
        return await response.json();
    } catch (error) {
        console.error("Error fetching categories:", error);
        return [];
    }
};

export const fetchSystemLogs = async () => {
    try {
        const response = await fetch(`${API_URL}/system-logs/`);
        if (!response.ok) throw new Error('Network response was not ok');
        return await response.json();
    } catch (error) {
        return []; // Return empty on error to avoid crashing UI
    }
};

export const fetchContainerStats = async () => {
    try {
        const response = await fetch(`${API_URL}/control/stats/`);
        if (!response.ok) throw new Error('Stats fetch failed');
        return await response.json();
    } catch (error) {
        console.error("Error fetching container stats:", error);
        return {};
    }
};

export const controlContainer = async (service, action) => {
    try {
        const response = await fetch(`${API_URL}/control/container/${service}/${action}/`, {
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
