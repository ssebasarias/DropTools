import React, { useState, useEffect } from 'react';
import { Play, Square, RotateCcw } from 'lucide-react';
import { controlContainer } from '../../../services/systemService';

const ServiceCard = ({ id, name, displayParams, icon: Icon, actions = [] }) => {
    const [loading, setLoading] = useState(false);
    const [stats, setStats] = useState(displayParams || { status: 'unknown', cpu: 0, ram_mb: 0 });

    // Update local stats when parent props change, ONLY if not currently processing an action
    useEffect(() => {
        if (displayParams && !loading) {
            setStats(displayParams);
        }
    }, [displayParams, loading]);

    const status = stats?.status || 'unknown';
    // Normalized states
    const isUpdating = status === 'updating...';
    const isRunning = status === 'running' || status === 'restarting' || (isUpdating && stats.cpu > 0);
    // If updating and we don't know, assume stopped to show Start button (safer) or just fallback.
    const isStopped = !isRunning && !isUpdating;

    // UI Colors based on status
    let statusColor = '#94a3b8'; // Default grey
    let bgColor = 'rgba(148, 163, 184, 0.1)';

    if (isRunning) {
        statusColor = '#10b981'; // Green
        bgColor = 'rgba(16, 185, 129, 0.1)';
    } else if (status === 'created') {
        statusColor = '#3b82f6'; // Blue
        bgColor = 'rgba(59, 130, 246, 0.1)';
    } else if (status === 'exited' || status === 'dead' || isStopped) {
        statusColor = '#64748b'; // Dark Grey
        bgColor = 'rgba(100, 116, 139, 0.1)';
    } else if (status === 'error') {
        statusColor = '#ef4444'; // Red
        bgColor = 'rgba(239, 68, 68, 0.1)';
    } else if (isUpdating) {
        statusColor = '#f59e0b'; // Amber/Orange
        bgColor = 'rgba(245, 158, 11, 0.1)';
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
                    <span style={{ marginLeft: 10, fontWeight: 'bold', color: '#fff' }}>Processing...</span>
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
                    {React.createElement(Icon, { size: 24 })}
                </div>
                <div style={{ flex: 1 }}>
                    <h4 style={{ marginBottom: 2, fontSize: '1rem', color: '#e2e8f0', margin: 0 }}>{name}</h4>
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
                        disabled={loading || isUpdating}
                        className="control-btn"
                        style={{ background: '#10b981', color: '#fff', flex: 1 }}
                    >
                        <Play size={16} fill="currentColor" /> Power ON
                    </button>
                )}

                {isRunning && (
                    <button
                        onClick={() => handleAction('stop')}
                        disabled={loading || isUpdating}
                        className="control-btn"
                        style={{ background: '#ef4444', color: '#fff', flex: 1 }}
                    >
                        <Square size={16} fill="currentColor" /> Stop
                    </button>
                )}

                {isUpdating && !isRunning && !isStopped && (
                    <button
                        disabled
                        className="control-btn"
                        style={{ background: '#f59e0b', color: '#fff', flex: 1, opacity: 0.8 }}
                    >
                        <RotateCcw size={16} className="spin" /> Processing...
                    </button>
                )}

                {actions.includes('restart') && isRunning && (
                    <button
                        onClick={() => handleAction('restart')}
                        disabled={loading || isUpdating}
                        className="control-btn"
                        style={{ background: '#3b82f6', color: '#fff', width: '40px', padding: 0 }}
                        title="Force Restart"
                    >
                        <RotateCcw size={16} />
                    </button>
                )}
            </div>
            {/* Styles for spinner if not global yet */}
            <style>{`
                .spinner {
                   width: 20px;
                   height: 20px;
                   border: 3px solid rgba(255,255,255,0.3);
                   border-radius: 50%;
                   border-top-color: #fff;
                   animation: spin 1s ease-in-out infinite;
                }
                @keyframes spin {
                   to { transform: rotate(360deg); }
                }
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

export default ServiceCard;
