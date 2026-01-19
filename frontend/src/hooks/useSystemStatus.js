import { useState, useEffect, useRef } from 'react';
import { fetchSystemLogs, fetchContainerStats } from '../services/systemService';

export const useSystemStatus = () => {
    const [logs, setLogs] = useState({}); // Default to Object now
    const [stats, setStats] = useState({});
    const [loading, setLoading] = useState(true);

    // Default to empty object for ref
    const prevLogsRef = useRef({});

    useEffect(() => {
        let statsInterval, logsInterval;

        const loadStats = async () => {
            if (document.hidden) return;
            try {
                const s = await fetchContainerStats();
                setStats(s || {});
            } catch (e) {
                console.error("Stats Error:", e);
            }
        };

        const loadLogs = async () => {
            if (document.hidden) return;
            try {
                const newLogs = await fetchSystemLogs();
                // newLogs is now a Dict: { "scraper": [...], ... }
                const l = newLogs || {};

                // Simple JSON comparison works well for tiered objects of this size (< 100KB)
                const hasChanged = JSON.stringify(l) !== JSON.stringify(prevLogsRef.current);

                if (hasChanged) {
                    prevLogsRef.current = l;
                    setLogs(l);
                }
            } catch (e) {
                console.error("Logs Error:", e);
            }
        };

        const init = async () => {
            await Promise.all([loadStats(), loadLogs()]);
            setLoading(false);
        };

        init();

        statsInterval = setInterval(loadStats, 2000);
        logsInterval = setInterval(loadLogs, 2000); // Faster polling since backend is parallelized

        return () => {
            clearInterval(statsInterval);
            clearInterval(logsInterval);
        };
    }, []);

    return { logs, stats, loading };
};
