import React, { useEffect, useState } from 'react';
import { fetchSystemLogs, fetchDashboardStats } from '../services/api';
import { Server, Database, Activity, Cpu, ShieldCheck } from 'lucide-react';
import './Dashboard.css';

const StatusCard = ({ name, status, icon: Icon }) => (
    <div className="glass-card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{
            padding: '1rem',
            borderRadius: 12,
            background: status === 'RUNNING' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
            color: status === 'RUNNING' ? '#10b981' : '#ef4444'
        }}>
            <Icon size={24} />
        </div>
        <div>
            <h4 style={{ marginBottom: 4 }}>{name}</h4>
            <span style={{
                fontSize: '0.8rem',
                fontWeight: 600,
                color: status === 'RUNNING' ? '#10b981' : '#ef4444'
            }}>
                {status}
            </span>
        </div>
    </div>
);

const LogTerminal = ({ title, logs, color = '#10b981' }) => {
    // Filtrar logs solo para este servicio
    const serviceLogs = logs.filter(l => l.service.toLowerCase() === title.toLowerCase());

    return (
        <div style={{
            background: '#0a0a0a',
            borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.1)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            height: 300
        }}>
            <div style={{
                padding: '0.5rem 1rem',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'rgba(255,255,255,0.02)'
            }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: color, textTransform: 'uppercase' }}>{title}</span>
                <span style={{ fontSize: '0.7rem', color: '#666' }}>
                    {serviceLogs.length > 0 && serviceLogs[serviceLogs.length - 1].message !== 'Log file not created yet.' ? 'ONLINE' : 'WAITING...'}
                </span>
            </div>
            <div style={{
                padding: '1rem',
                flex: 1,
                overflowY: 'auto',
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                color: '#e2e8f0'
            }}>
                {serviceLogs.length === 0 && <span style={{ color: '#444' }}>Waiting for logs...</span>}
                {serviceLogs.slice(-20).map((log, i) => (
                    <div key={i} style={{ marginBottom: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {log.message}
                    </div>
                ))}
            </div>
        </div>
    );
};

const SystemStatus = () => {
    const [logs, setLogs] = useState([]);
    const [kpis, setKpis] = useState({});

    // Services status mockup
    const services = [
        { name: "Scraper Core", status: "RUNNING", icon: Activity },
        { name: "Cluster AI", status: "RUNNING", icon: Cpu },
        { name: "Vector Database", status: "RUNNING", icon: Database },
        { name: "Backend API", status: "RUNNING", icon: Server },
        { name: "DroPi Connection", status: "RUNNING", icon: ShieldCheck },
    ];

    useEffect(() => {
        const loadData = async () => {
            // Fetch logs (Priority 1)
            try {
                const logData = await fetchSystemLogs();
                if (logData && Array.isArray(logData)) setLogs(logData);
            } catch (err) {
                console.error("Error loading logs:", err);
            }

            // Fetch metrics (Priority 2)
            try {
                const statsData = await fetchDashboardStats();
                if (statsData) setKpis(statsData);
            } catch (err) {
                console.error("Error loading stats:", err);
            }
        };

        loadData();
        const interval = setInterval(loadData, 3000); // Poll faster (3s)
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="dashboard-container">
            <div className="header-greeting">
                <h1>System Status</h1>
                <p>Cuarto de Máquinas: Monitoreo en Tiempo Real</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                {services.map(s => <StatusCard key={s.name} {...s} />)}
            </div>

            {/* Nuevas Métricas de Salud (KPIs) */}
            <h3 style={{ marginBottom: '1rem' }}>System Health KPIs</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>

                {/* 1. Backlog de Archivos */}
                <div className="glass-card" style={{ padding: '1.5rem' }}>
                    <h4 style={{ color: '#aaa', fontSize: '0.9rem', marginBottom: '0.5rem' }}>Raw Files Queue</h4>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                        {kpis.backlog_metrics?.jsonl_files ?? 0}
                    </div>
                    <span style={{ fontSize: '0.8rem', color: '#666' }}>Pending .jsonl files</span>
                </div>

                {/* 2. Pendientes de Vectorizar */}
                <div className="glass-card" style={{ padding: '1.5rem' }}>
                    <h4 style={{ color: '#aaa', fontSize: '0.9rem', marginBottom: '0.5rem' }}>Pending Vectorization</h4>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: (kpis.backlog_metrics?.pending_vectors > 1000) ? '#f59e0b' : '#fff' }}>
                        {kpis.backlog_metrics?.pending_vectors ?? 0}
                    </div>
                    <span style={{ fontSize: '0.8rem', color: '#666' }}>Products waiting for AI</span>
                </div>

                {/* 3. Tasa de Errores */}
                <div className="glass-card" style={{ padding: '1.5rem', border: (kpis.backlog_metrics?.recent_errors > 0) ? '1px solid #ef4444' : '1px solid rgba(255,255,255,0.1)' }}>
                    <h4 style={{ color: '#aaa', fontSize: '0.9rem', marginBottom: '0.5rem' }}>Recent Errors (1h)</h4>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: (kpis.backlog_metrics?.recent_errors > 0) ? '#ef4444' : '#10b981' }}>
                        {kpis.backlog_metrics?.recent_errors ?? 0}
                    </div>
                    <span style={{ fontSize: '0.8rem', color: '#666' }}>Exceptions in logs</span>
                </div>
            </div>

            <h3 style={{ marginBottom: '1rem' }}>Live Service Terminals</h3>

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
                gap: '1.5rem'
            }}>
                <LogTerminal title="scraper" logs={logs} color="#f59e0b" />
                <LogTerminal title="loader" logs={logs} color="#3b82f6" />
                <LogTerminal title="vectorizer" logs={logs} color="#a855f7" />
                <LogTerminal title="clusterizer" logs={logs} color="#10b981" />
            </div>
        </div>
    );
};

export default SystemStatus;
