import { useState, useEffect, useCallback } from 'react';
import { fetchAuditLogs, fetchOrphans, fetchClusterStats } from '../services/clusterService';

export const useClusterLab = () => {
    const [logs, setLogs] = useState([]);
    const [orphans, setOrphans] = useState([]);
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);

    const refreshData = useCallback(async () => {
        const [newLogs, newOrphans, newMetrics] = await Promise.all([
            fetchAuditLogs(),
            fetchOrphans(),
            fetchClusterStats()
        ]);

        setLogs(newLogs);
        setOrphans(newOrphans);
        setMetrics(newMetrics);
        setLoading(false);
    }, []);

    useEffect(() => {
        const t = setTimeout(() => refreshData(), 0);
        const interval = setInterval(refreshData, 3000); // Polling every 3s
        return () => {
            clearTimeout(t);
            clearInterval(interval);
        };
    }, [refreshData]);

    return { logs, orphans, metrics, loading, refreshData };
};
