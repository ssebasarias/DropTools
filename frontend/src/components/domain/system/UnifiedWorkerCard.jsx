import React, { useState, useEffect, useRef } from 'react';
import { Play, Square, RotateCcw, Power, Terminal } from 'lucide-react';
import { controlContainer } from '../../../services/systemService';

const UnifiedWorkerCard = ({ id, name, icon: Icon, logs = {}, displayParams, actions = [], color = '#10b981' }) => {
    const [loading, setLoading] = useState(false);
    const [stats, setStats] = useState(displayParams || { status: 'unknown', cpu: 0, ram_mb: 0 });
    const terminalRef = useRef(null);
    const shouldAutoScrollRef = useRef(true); // Track if we should stick to bottom
    const [showScrollButton, setShowScrollButton] = useState(false); // UI toggle for scroll button

    // Update local stats when parent props change
    useEffect(() => {
        if (displayParams && !loading) {
            setStats(displayParams);
        }
    }, [displayParams, loading]);

    const serviceLogs = logs[id] || [];
    const status = stats?.status || 'unknown';
    const isUpdating = status === 'updating...';
    // Consideramos corriendo si status es 'running' o 'restarting'
    const isRunning = status === 'running' || status === 'restarting';
    const isStopped = !isRunning && !isUpdating;

    // Handle user manual scrolling
    const handleScroll = () => {
        const term = terminalRef.current;
        if (!term) return;
        const { scrollTop, scrollHeight, clientHeight } = term;
        // If user is within 50px of bottom, sticky mode is ON. Otherwise OFF.
        const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

        shouldAutoScrollRef.current = isAtBottom;

        // Toggle button visibility based on scroll position
        if (isAtBottom && showScrollButton) setShowScrollButton(false);
        if (!isAtBottom && !showScrollButton) setShowScrollButton(true);
    };

    // Auto-scroll logic with LayoutEffect to prevent flicker
    React.useLayoutEffect(() => {
        const term = terminalRef.current;
        if (term && serviceLogs.length > 0) {
            // Apply scroll only if sticky mode is active
            if (shouldAutoScrollRef.current) {
                term.scrollTop = term.scrollHeight;
            }
        }
    }, [logs, serviceLogs.length]);

    const scrollBottom = () => {
        const term = terminalRef.current;
        if (term) {
            term.scrollTop = term.scrollHeight;
            shouldAutoScrollRef.current = true;
            setShowScrollButton(false);
        }
    };

    let statusColor = '#64748b'; // Default grey
    if (isRunning) statusColor = '#10b981'; // Green
    else if (status === 'created') statusColor = '#3b82f6'; // Blue
    else if (status === 'error') statusColor = '#ef4444'; // Red
    else if (isUpdating) statusColor = '#f59e0b'; // Amber

    const handleAction = async (action) => {
        if (loading) return;
        setLoading(true);
        try {
            await controlContainer(id, action);
            if (action === 'start') setStats(s => ({ ...s, status: 'running' }));
            if (action === 'stop') setStats(s => ({ ...s, status: 'exited', cpu: 0, ram_mb: 0 }));
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
            borderTop: `3px solid ${color}`, // Use section-themed color for top border
            background: 'rgba(20, 20, 25, 0.6)',
            backdropFilter: 'blur(12px)',
            borderRadius: '16px',
            border: '1px solid rgba(255,255,255,0.05)',
            boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.3)',
            height: '100%',
        }}>
            {/* Header: Name + Status */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{
                        padding: '0.5rem',
                        borderRadius: '10px',
                        background: `${color}20`,
                        color: color
                    }}>
                        {React.createElement(Icon, { size: 20 })}
                    </div>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#e2e8f0', fontWeight: 600 }}>{name}</h3>
                </div>

                {/* Status Indicator */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        backgroundColor: statusColor,
                        boxShadow: isRunning ? `0 0 8px ${statusColor}` : 'none',
                        transition: 'all 0.3s ease'
                    }} />
                    <span style={{
                        fontSize: '0.75rem',
                        color: statusColor,
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                    }}>
                        {status === 'unknown' ? 'OFFLINE' : status}
                    </span>
                </div>
            </div>

            {/* Controls & Metrics Row */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                gap: '1rem',
                alignItems: 'center'
            }}>
                {/* Control Buttons */}
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {isStopped && (
                        <button onClick={() => handleAction('start')} disabled={loading} className="action-btn start" title="Start Service">
                            <Play size={16} fill="currentColor" />
                        </button>
                    )}
                    {isRunning && (
                        <button onClick={() => handleAction('stop')} disabled={loading} className="action-btn stop" title="Stop Service">
                            <Square size={16} fill="currentColor" />
                        </button>
                    )}
                    {actions.includes('restart') && isRunning && (
                        <button onClick={() => handleAction('restart')} disabled={loading} className="action-btn restart" title="Restart Service">
                            <RotateCcw size={16} />
                        </button>
                    )}
                    {loading && <span className="spinner-mini"></span>}
                </div>

                {/* Mini Metrics */}
                <div style={{
                    display: 'flex',
                    gap: '0.75rem',
                    fontSize: '0.75rem',
                    color: '#94a3b8',
                    background: 'rgba(0,0,0,0.2)',
                    padding: '0.35rem 0.75rem',
                    borderRadius: '20px'
                }}>
                    <span>CPU: <strong style={{ color: '#fff' }}>{isRunning ? stats.cpu : 0}%</strong></span>
                    <span style={{ width: 1, background: 'rgba(255,255,255,0.1)' }}></span>
                    <span>RAM: <strong style={{ color: '#fff' }}>{isRunning ? stats.ram_mb : 0}MB</strong></span>
                </div>
            </div>

            {/* Embedded Terminal */}
            <div style={{
                marginTop: '0.5rem',
                background: '#09090b',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.05)',
                display: 'flex',
                flexDirection: 'column',
                flex: 1,
                minHeight: '200px',
                maxHeight: '200px', // Fixed height as requested
                overflow: 'hidden',
                position: 'relative'
            }}>
                {/* Stopped Overlay */}
                {isStopped && (
                    <div style={{
                        position: 'absolute', inset: 0,
                        background: 'rgba(0,0,0,0.6)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        zIndex: 10,
                        backdropFilter: 'grayscale(100%)'
                    }}>
                        <span style={{ color: '#94a3b8', fontSize: '0.8rem', fontStyle: 'italic', background: 'rgba(0,0,0,0.8)', padding: '4px 12px', borderRadius: '4px' }}>
                            Service Stopped - Logs Frozen
                        </span>
                    </div>
                )}

                <div style={{
                    padding: '0.4rem 0.75rem',
                    background: 'rgba(255,255,255,0.03)',
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                }}>
                    <Terminal size={12} color="#64748b" />
                    <span style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '1px' }}>System Output</span>
                </div>


                {/* Scroll to Bottom Button */}
                {showScrollButton && (
                    <button
                        onClick={scrollBottom}
                        style={{
                            position: 'absolute',
                            bottom: '10px',
                            right: '20px',
                            background: color,
                            color: '#000',
                            border: 'none',
                            borderRadius: '20px',
                            padding: '4px 12px',
                            fontSize: '0.7rem',
                            fontWeight: 'bold',
                            cursor: 'pointer',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                            zIndex: 20,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                        }}
                    >
                        <span>⬇</span> Auto-Scroll Paused
                    </button>
                )}

                <div
                    onScroll={handleScroll}
                    ref={terminalRef} style={{
                        padding: '0.75rem',
                        fontFamily: "'Fira Code', 'Consolas', monospace",
                        fontSize: '0.7rem',
                        color: color, // Use service theme color for text
                        overflowY: 'auto',
                        flex: 1,
                        lineHeight: '1.5',
                        // scrollBehavior: 'smooth' // REMOVED: Causes fighting with auto-scroll logic
                    }}>
                    {serviceLogs.length === 0 ? (
                        <span style={{ opacity: 0.3, fontStyle: 'italic' }}>// No active logs...</span>
                    ) : (
                        serviceLogs.slice(-50).map((log, i) => {
                            // Calculate a stable index for the key to prevent re-rendering all rows
                            // and allow browser scroll anchoring to work.
                            const stableKey = serviceLogs.length > 50
                                ? serviceLogs.length - 50 + i
                                : i;

                            // Determine log style
                            const msgLower = (log.message || "").toLowerCase();
                            let logColor = 'inherit'; // Default uses parent color (usually theme color)
                            let fontWeight = 'normal';

                            if (msgLower.includes('error') || msgLower.includes('❌') || msgLower.includes('exception') || msgLower.includes('traceback') || msgLower.includes('fail')) {
                                logColor = '#ef4444'; // Red
                                fontWeight = 'bold';
                            } else if (msgLower.includes('warning') || msgLower.includes('warn') || msgLower.includes('⚠️')) {
                                logColor = '#f59e0b'; // Amber
                            } else if (msgLower.includes('success') || msgLower.includes('✅') || msgLower.includes('🚀') || msgLower.includes('completa')) {
                                logColor = '#10b981'; // Green
                            } else if (msgLower.includes('procesan') || msgLower.includes('leyendo') || msgLower.includes('📊') || msgLower.includes('verificado')) {
                                logColor = '#3b82f6'; // Blue
                            } else if (msgLower.startsWith('...')) {
                                logColor = '#94a3b8'; // Dimmed for progress
                            }

                            return (
                                <div key={stableKey} style={{ marginBottom: '2px', wordBreak: 'break-all', color: logColor !== 'inherit' ? logColor : undefined, fontWeight }}>
                                    <span style={{ opacity: 0.5, marginRight: '6px' }}>&gt;</span>
                                    {log.message}
                                </div>
                            );
                        })
                    )}
                </div>
            </div>

            <style>{`
                .action-btn {
                    border: none;
                    border-radius: 8px;
                    width: 32px;
                    height: 32px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    transition: all 0.2s;
                    color: #fff;
                }
                .action-btn:hover { transform: translateY(-2px); filter: brightness(1.2); }
                .action-btn:active { transform: translateY(0); }
                .action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
                
                .action-btn.start { background: #10b981; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); }
                .action-btn.stop { background: #ef4444; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3); }
                .action-btn.restart { background: #3b82f6; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }

                .spinner-mini {
                    width: 16px;
                    height: 16px;
                    border: 2px solid rgba(255,255,255,0.1);
                    border-top-color: #fff;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin-left: 0.5rem;
                }
            `}</style>
        </div>
    );
};

export default UnifiedWorkerCard;
