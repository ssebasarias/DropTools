/**
 * Cluster Service - DropTools Frontend
 * Servicios para Cluster Lab
 */
import { API_BASE_URL } from '../config/constants';

// URL Base del Backend
const API_URL = API_BASE_URL;

// --- CLUSTER LAB SERVICES ---

export const fetchAuditLogs = async () => {
    try {
        const res = await fetch(`${API_URL}/cluster-lab/audit-logs/`);
        if (!res.ok) throw new Error('Failed to fetch logs');
        return await res.json();
    } catch (err) {
        console.error("Error fetching logs:", err);
        return [];
    }
};

export const fetchOrphans = async () => {
    try {
        const res = await fetch(`${API_URL}/cluster-lab/orphans/`);
        if (!res.ok) throw new Error('Failed to fetch orphans');
        return await res.json();
    } catch (err) {
        console.error("Error fetching orphans:", err);
        return [];
    }
};

export const fetchClusterStats = async () => {
    try {
        const res = await fetch(`${API_URL}/cluster-lab/stats/`);
        if (!res.ok) throw new Error('Failed to fetch stats');
        return await res.json();
    } catch (err) {
        console.error("Error fetching cluster stats:", err);
        return null;
    }
};

export const saveClusterFeedback = async (payload) => {
    const res = await fetch(`${API_URL}/cluster-lab/feedback/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Feedback failed');
    return await res.json();
};

export const investigateOrphan = async (productId) => {
    const res = await fetch(`${API_URL}/cluster-lab/orphans/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId })
    });
    if (!res.ok) throw new Error('Investigation failed');
    return await res.json();
};

export const executeOrphanAction = async (payload) => {
    const res = await fetch(`${API_URL}/cluster-lab/orphans/action/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Action failed');
    return await res.json();
};
