import React, { useEffect, useState } from 'react';
import { fetchSystemLogs, fetchContainerStats, controlContainer } from '../services/api';
import { Server, Database, Activity, Cpu, Play, Square, RotateCcw, Power, AlertCircle } from 'lucide-react';
import './Dashboard.css';

const ServiceCard = ({ id, name, displayParams, icon: Icon, actions = [] }) => {
    const [loading, setLoading] = useState(false);
    const [stats, setStats] = useState(displayParams || { status: 'unknown', cpu: 0, ram_mb: 0 });

    // Update local stats when parent props change
    useEffect(() => {
        if (displayParams) setStats(displayParams);
    }, [displayParams]);

    const status = stats?.status || 'unknown';
    const isRunning = status === 'running';
    const isStopped = ['exited', 'created', 'not_found', 'none', 'unknown'].includes(status);

    // UI Colors based on status
    let statusColor = '#94a3b8'; // Default grey
    let bgColor = 'rgba(148, 163, 184, 0.1)';

    if (isRunning) {
        statusColor = '#10b981'; // Green
        bgColor = 'rgba(16, 185, 129, 0.1)';
    } else if (status === 'created') {
        statusColor = '#3b82f6'; // Blue
        bgColor = 'rgba(59, 130, 246, 0.1)';
    } else if (status === 'exited') {
        statusColor = '#64748b'; // Dark Grey
        bgColor = 'rgba(100, 116, 139, 0.1)';
    } else if (status === 'error') {
        statusColor = '#ef4444'; // Red
        bgColor = 'rgba(239, 68, 68, 0.1)';
    }

    const handleAction = async (action) => {
        if (loading) return;
        setLoading(true);
        try {
            await controlContainer(id, action);
            // Optimistic update
            if (action === 'start') setStats(s => ({ ...s, status: 'running' }));
            if (action === 'stop') setStats(s => ({ ...s, status: 'exited', cpu: 0, ram_mb: 0 }));
            // Parent polling will correct state in <3s
        } catch (err) {
            alert(`Error: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="glass-card" style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            padding: '1.25rem',
            borderTop: `3px solid ${statusColor}`,
            position: 'relative',
            overflow: 'hidden'
        }}>
            {loading && (
                <div style={{
                    position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10
                }}>
                    <div className="spinner"></div>
                    {/* Add simple spinner css later or assume it exists/simple text */}
                    <span style={{ marginLeft: 10, fontWeight: 'bold' }}>Processing...</span>
                </div>
            )}

            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{
                    padding: '0.75rem',
                    borderRadius: 12,
                    background: bgColor,
                    color: statusColor,
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                    <Icon size={24} />
                </div>
                <div style={{ flex: 1 }}>
                    <h4 style={{ marginBottom: 2, fontSize: '1rem', color: '#e2e8f0' }}>{name}</h4>
                    <span style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        color: statusColor,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                    }}>
                        {status.replace('_', ' ')}
                    </span>
                </div>
            </div>

            {/* Metrics */}
            <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr',
                gap: '1px', background: 'rgba(255,255,255,0.1)',
                padding: '1px', borderRadius: 8, overflow: 'hidden'
            }}>
                <div style={{ textAlign: 'center', background: 'rgba(0,0,0,0.2)', padding: '0.5rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>CPU Usage</div>
                    <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#f8fafc' }}>
                        {isRunning ? `${stats?.cpu || 0}%` : '-'}
                    </div>
                </div>
                <div style={{ textAlign: 'center', background: 'rgba(0,0,0,0.2)', padding: '0.5rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>RAM Usage</div>
                    <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#f8fafc' }}>
                        {isRunning ? `${stats?.ram_mb || 0} MB` : '-'}
                    </div>
                </div>
            </div>

            {/* Controls */}
            <div style={{ display: 'flex', gap: '0.75rem', marginTop: 'auto' }}>
                {isStopped && (
                    <button
                        onClick={() => handleAction('start')}
                        disabled={loading}
                        className="control-btn"
                        style={{ background: '#10b981', color: '#fff', flex: 1 }}
                    >
                        <Play size={16} fill="currentColor" /> Power ON
                    </button>
                )}

                {isRunning && (
                    <button
                        onClick={() => handleAction('stop')}
                        disabled={loading}
                        className="control-btn"
                        style={{ background: '#ef4444', color: '#fff', flex: 1 }}
                    >
                        <Square size={16} fill="currentColor" /> Stop
                    </button>
                )}

                {actions.includes('restart') && isRunning && (
                    <button
                        onClick={() => handleAction('restart')}
                        disabled={loading}
                        className="control-btn"
                        style={{ background: '#3b82f6', color: '#fff', width: '40px', padding: 0 }}
                        title="Force Restart"
                    >
                        <RotateCcw size={16} />
                    </button>
                )}
            </div>

            <style>{`
                .control-btn {
                    border: none;
                    border-radius: 8px;
                    padding: 0.6rem;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.5rem;
                    font-size: 0.85rem;
                    font-weight: 600;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                    transition: all 0.2s;
                }
                .control-btn:hover { filter: brightness(1.1); transform: translateY(-1px); }
                .control-btn:active { transform: translateY(0); }
                .control-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
            `}</style>
        </div>
    );
};

const LogTerminal = ({ title, logs, color = '#10b981' }) => {
    const serviceLogs = logs.filter(l => l.service.toLowerCase() === title.toLowerCase());
    return (
        <div style={{
            background: '#09090b',
            borderRadius: 12,
            border: '1px solid rgba(255,255,255,0.08)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            height: 320,
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)'
        }}>
            <div style={{
                padding: '0.75rem 1rem',
                borderBottom: '1px solid rgba(255,255,255,0.08)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'rgba(255,255,255,0.03)'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}` }}></div>
                    <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#e2e8f0', textTransform: 'uppercase' }}>{title}</span>
                </div>
                <span style={{ fontSize: '0.7rem', color: '#64748b', fontFamily: 'monospace' }}>
                    {serviceLogs.length > 0 ? 'LIVE' : 'IDLE'}
                </span>
            </div>
            <div className="terminal-body" style={{
                padding: '1rem',
                flex: 1,
                overflowY: 'auto',
                fontFamily: "'Fira Code', 'Consolas', monospace",
                fontSize: '0.75rem',
                color: '#e2e8f0',
                lineHeight: '1.5'
            }}>
                {serviceLogs.length === 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#334155' }}>
                        <span style={{ fontStyle: 'italic' }}>Waiting for logs...</span>
                    </div>
                )}
                {serviceLogs.slice(-30).map((log, i) => (
                    <div key={i} style={{ marginBottom: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-word', display: 'flex' }}>
                        <span style={{ color: '#475569', marginRight: '0.5rem', userSelect: 'none' }}>$</span>
                        <span>{log.message}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

const SystemStatus = () => {
    const [logs, setLogs] = useState([]);
    const [stats, setStats] = useState({});

    // Load Stats Fast (2s) - CON MODO SIESTA
    useEffect(() => {
        let interval;
        const loadStats = async () => {
            // Si la pestaña está oculta, no hacemos nada (ahorro de recursos)
            if (document.hidden) return;
            try {
                const s = await fetchContainerStats();
                setStats(s || {});
            } catch (e) {
                console.error("Stats Error:", e);
            }
        };

        loadStats();
        interval = setInterval(loadStats, 2000);
        return () => clearInterval(interval);
    }, []);

    // Load Logs Slow (5s) - CON MODO SIESTA
    useEffect(() => {
        let interval;
        const loadLogs = async () => {
            if (document.hidden) return;
            try {
                const l = await fetchSystemLogs();
                setLogs(l || []);
            } catch (e) {
                console.error("Logs Error:", e);
            }
        };

        loadLogs();
        interval = setInterval(loadLogs, 5000);
        return () => clearInterval(interval);
    }, []);

    const serviceConfig = [
        { id: 'scraper', name: 'Web Scraper', icon: Activity, actions: ['restart'] },
        { id: 'loader', name: 'Data Loader', icon: Database, actions: ['restart'] },
        { id: 'vectorizer', name: 'AI Vectorizer', icon: Cpu, actions: ['restart'] },
        { id: 'clusterizer', name: 'Cluster Engine', icon: Server, actions: ['restart'] },
        { id: 'ai_trainer', name: 'AI Trainer (Cerebro)', icon: Activity, actions: ['restart'] },
    ];

    return (
        <div className="dashboard-container" style={{ maxWidth: '1600px', margin: '0 auto', padding: '2rem' }}>
            <div className="header-greeting" style={{ textAlign: 'center', marginBottom: '3rem' }}>
                <h1 style={{ fontSize: '2.5rem', background: 'linear-gradient(to right, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    Command Center
                </h1>
                <p style={{ color: '#64748b' }}>Infraestructure Management & Real-time Telemetry</p>
            </div>

            {/* CONTROL PANEL */}
            <div style={{
                background: 'rgba(255,255,255,0.02)',
                borderRadius: '16px',
                padding: '2rem',
                border: '1px solid rgba(255,255,255,0.05)',
                marginBottom: '3rem'
            }}>
                <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#e2e8f0' }}>
                    <Power size={20} color="#3b82f6" /> Active Services Control
                </h3>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
                    {serviceConfig.map(svc => (
                        <ServiceCard
                            key={svc.id}
                            {...svc}
                            displayParams={stats[svc.id]}
                        />
                    ))}
                </div>
            </div>

            {/* LOGS SECTION */}
            <div>
                <h3 style={{ marginBottom: '1.5rem', color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <AlertCircle size={20} color="#f59e0b" /> Live Execution Logs
                </h3>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
                    gap: '1.5rem'
                }}>
                    <LogTerminal title="scraper" logs={logs} color="#f59e0b" />
                    <LogTerminal title="loader" logs={logs} color="#3b82f6" />
                    <LogTerminal title="vectorizer" logs={logs} color="#a855f7" />
                    <LogTerminal title="clusterizer" logs={logs} color="#10b981" />
                    <LogTerminal title="ai_trainer" logs={logs} color="#ec4899" />
                </div>
            </div>
        </div>
    );
};

export default SystemStatus;
