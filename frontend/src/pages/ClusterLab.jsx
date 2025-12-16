import React, { useState, useEffect } from 'react';
import { Layers, Activity, Search, AlertCircle, BarChart2, Eye, FileText, CheckCircle, XCircle, X } from 'lucide-react';
import './ClusterLab.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Components
const AuditModal = ({ log, onClose }) => {
    const [status, setStatus] = useState('idle'); // idle, saving, success, error

    if (!log) return null;

    const handleFeedback = async (feedbackType) => {
        setStatus('saving');
        try {
            await fetch(`${API_URL}/api/cluster-lab/feedback/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_id: log.product_id,
                    candidate_id: log.candidate_id,
                    decision: log.decision,
                    feedback: feedbackType === 'correct' ? 'CORRECT' : 'INCORRECT',

                    // Rich Data for AI Trainer
                    visual_score: log.visual_score,
                    text_score: log.text_score,
                    final_score: log.final_score,
                    method: log.method,
                    active_weights: log.active_weights // Enviamos el snapshot que guardo el log
                })
            });
            setStatus('success');
            setTimeout(() => onClose(), 1000); // Close after 1s delay
        } catch (err) {
            console.error("Error saving feedback:", err);
            setStatus('error');
        }
    };

    return (
        <div className="audit-modal-overlay" onClick={onClose}>
            <div className="audit-modal-content glass-panel" onClick={e => e.stopPropagation()}>
                <button className="close-btn" onClick={onClose}><X size={24} /></button>

                {status === 'success' ? (
                    <div style={{ textAlign: 'center', padding: '4rem' }}>
                        <CheckCircle size={64} color="#10b981" style={{ margin: '0 auto 1rem' }} />
                        <h2 style={{ color: '#10b981' }}>¡Feedback Guardado!</h2>
                        <p style={{ color: '#94a3b8' }}>El cerebro ha aprendido de esta decisión.</p>
                    </div>
                ) : (
                    <>
                        <div className="audit-header">
                            <h2>Auditoría de Decisión IA</h2>
                            <span className={`badge badge-${log.decision === 'JOINED_CLUSTER' ? 'success' : 'warning'}`}>
                                {log.decision}
                            </span>
                        </div>

                        <div className="vs-container">
                            {/* Product A (Base) */}
                            <div className="product-card-compare">
                                <div className="img-wrapper">
                                    <img src={log.image_a || 'https://via.placeholder.com/300?text=No+Image'} alt="Base Product" />
                                </div>
                                <div className="info">
                                    <h4>{log.title_a || 'Producto Base'}</h4>
                                    <span className="id-tag">ID: {log.product_id}</span>
                                </div>
                            </div>

                            {/* VS Stats */}
                            <div className="vs-stats">
                                <div className="score-circle">
                                    <span className="score-val">{(log.final_score * 100).toFixed(0)}%</span>
                                    <span className="score-label">MATCH</span>
                                </div>
                                <div className="stat-bars">
                                    <div className="bar-group">
                                        <label><Eye size={12} /> Visual</label>
                                        <div className="bar-bg"><div className="bar-fill visual" style={{ width: `${log.visual_score * 100}%` }}></div></div>
                                        <span>{Math.round(log.visual_score * 100)}%</span>
                                    </div>
                                    <div className="bar-group">
                                        <label><FileText size={12} /> Texto</label>
                                        <div className="bar-bg"><div className="bar-fill text" style={{ width: `${log.text_score * 100}%` }}></div></div>
                                        <span>{Math.round(log.text_score * 100)}%</span>
                                    </div>
                                </div>
                                <span className="method-tag">{log.method}</span>
                            </div>

                            {/* Product B (Candidate) */}
                            <div className="product-card-compare">
                                <div className="img-wrapper">
                                    <img src={log.image_b || 'https://via.placeholder.com/300?text=No+Image'} alt="Candidate" />
                                </div>
                                <div className="info">
                                    <h4>{log.title_b || 'Candidato'}</h4>
                                    <span className="id-tag">ID: {log.candidate_id}</span>
                                </div>
                            </div>
                        </div>

                        <div className="audit-actions">
                            <p>¿Es correcta esta decisión?</p>
                            <div className="buttons">
                                <button className="btn-action happy" onClick={() => handleFeedback('correct')} disabled={status === 'saving'} title="Correcto (Reforzar)">
                                    <CheckCircle size={20} /> Correcto
                                </button>
                                <button className="btn-action sad" onClick={() => handleFeedback('incorrect')} disabled={status === 'saving'} title="Incorrecto (Corregir)">
                                    <XCircle size={20} /> Incorrecto
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </div>
            <style jsx>{`
                .audit-modal-overlay {
                    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                    background: rgba(0,0,0,0.8); backdrop-filter: blur(8px);
                    display: flex; align-items: center; justify-content: center;
                    z-index: 1000;
                }
                .audit-modal-content {
                    width: 90%; max-width: 900px; padding: 2rem;
                    position: relative; border: 1px solid rgba(255,255,255,0.1);
                    max-height: 90vh; overflow-y: auto;
                }
                .close-btn {
                    position: absolute; top: 1rem; right: 1rem;
                    background: none; border: none; color: #fff; cursor: pointer;
                }
                .audit-header { text-align: center; margin-bottom: 2rem; }
                .vs-container {
                    display: grid; grid-template-columns: 1fr 200px 1fr; gap: 1rem;
                    align-items: center; margin-bottom: 2rem;
                }
                .product-card-compare {
                    background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 12px;
                    text-align: center;
                }
                .img-wrapper {
                    width: 100%; height: 200px; background: #000; border-radius: 8px;
                    overflow: hidden; margin-bottom: 1rem;
                }
                .img-wrapper img { width: 100%; height: 100%; object-fit: contain; }
                .score-circle {
                    width: 80px; height: 80px; border-radius: 50%;
                    border: 4px solid #6366f1; display: flex; flex-direction: column;
                    align-items: center; justify-content: center; margin: 0 auto 1rem;
                }
                .score-val { font-size: 1.5rem; font-weight: bold; color: #fff; }
                .score-label { font-size: 0.6rem; color: #ccc; }
                .bar-group { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; font-size: 0.8rem; color: #ccc; }
                .bar-bg { flex: 1; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; }
                .bar-fill.visual { background: #3b82f6; height: 100%; }
                .bar-fill.text { background: #8b5cf6; height: 100%; }
                .audit-actions { text-align: center; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 1.5rem; }
                .buttons { display: flex; justify-content: center; gap: 1rem; margin-top: 1rem; }
                .btn-action {
                    padding: 0.75rem 2rem; border-radius: 8px; border: none; font-weight: bold; cursor: pointer;
                    display: flex; align-items: center; gap: 0.5rem; color: #fff;
                }
                .btn-action.happy { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); }
                .btn-action.happy:hover { background: rgba(16, 185, 129, 0.4); }
                .btn-action.sad { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); }
                .btn-action.sad:hover { background: rgba(239, 68, 68, 0.4); }
            `}</style>
        </div>
    );
};

const ClusterLab = () => {
    const [auditLogs, setAuditLogs] = useState([]);
    const [orphans, setOrphans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('audit');

    const [selectedLog, setSelectedLog] = useState(null); // For Modal 
    const [simulationData, setSimulationData] = useState(null); // For Orphan Simulation Modal

    const handleAuditOrphan = async (orphan) => {
        try {
            const res = await fetch(`${API_URL}/api/cluster-lab/orphans/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_id: orphan.product_id })
            });
            if (res.ok) {
                const data = await res.json();
                // Pick the best candidate (top 1) even if rejected, to show "Why it failed".
                const best = data.candidates[0];
                if (best) {
                    setSelectedLog({
                        title_a: data.target.title,
                        product_id: data.target.id,
                        image_a: orphan.image,

                        title_b: best.title,
                        candidate_id: best.id,
                        image_b: best.image,

                        visual_score: best.scores.visual,
                        text_score: best.scores.text,
                        final_score: best.scores.final,
                        decision: best.would_match ? 'HYPOTHETICAL_MATCH' : 'REJECTED_SIMULATION',
                        method: best.method
                    });
                } else {
                    alert("No se encontraron candidatos cercanos para este huérfano.");
                }
            }
        } catch (err) {
            console.error(err);
        }
    };




    // Polling function for logs
    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const res = await fetch(`${API_URL}/api/cluster-lab/audit-logs/`);
                if (res.ok) {
                    const data = await res.json();
                    setAuditLogs(data);
                }
            } catch (err) {
                console.error("Error fetching audit logs", err);
            }
        };

        const fetchOrphans = async () => {
            try {
                const res = await fetch(`${API_URL}/api/cluster-lab/orphans/`);
                if (res.ok) {
                    const data = await res.json();
                    setOrphans(data);
                }
            } catch (err) {
                console.error("Error fetching orphans", err);
            }
            setLoading(false);
        };

        fetchLogs();
        fetchOrphans();

        // Refresh logs every 3 seconds
        const interval = setInterval(fetchLogs, 3000);
        return () => clearInterval(interval);
    }, []);

    const getScoreColor = (score) => {
        if (score >= 0.8) return '#10b981'; // Green
        if (score >= 0.5) return '#f59e0b'; // Amber
        return '#ef4444'; // Red
    };

    return (
        <div style={{ padding: '2rem', maxWidth: '1600px', margin: '0 auto', color: '#fff' }}>

            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 className="text-gradient" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '2rem' }}>
                        <Layers size={32} /> Cluster Lab <span style={{ fontSize: '0.8rem', background: '#6366f1', padding: '0.2rem 0.5rem', borderRadius: 4, verticalAlign: 'middle' }}>V3 HYBRID</span>
                    </h1>
                    <p style={{ color: '#94a3b8', marginTop: '0.5rem' }}>
                        Centro de Auditoría Neuronal: Visualización en tiempo real del motor de clustering.
                    </p>
                </div>

                <div className="glass-panel" style={{ padding: '0.5rem', display: 'flex', gap: '0.5rem' }}>
                    <button
                        className={`btn-tab ${activeTab === 'audit' ? 'active' : ''}`}
                        onClick={() => setActiveTab('audit')}
                        style={{ background: activeTab === 'audit' ? 'rgba(99, 102, 241, 0.2)' : 'transparent', border: 'none', color: '#fff', padding: '0.5rem 1rem', borderRadius: 6, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                    >
                        <Activity size={18} /> Consola en Vivo
                    </button>
                    <button
                        className={`btn-tab ${activeTab === 'orphans' ? 'active' : ''}`}
                        onClick={() => setActiveTab('orphans')}
                        style={{ background: activeTab === 'orphans' ? 'rgba(99, 102, 241, 0.2)' : 'transparent', border: 'none', color: '#fff', padding: '0.5rem 1rem', borderRadius: 6, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                    >
                        <AlertCircle size={18} /> Huérfanos ({orphans.length})
                    </button>
                </div>
            </div>

            {/* LIVE CONSOLE TAB */}
            {activeTab === 'audit' && (
                <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '1.5rem' }}>

                    {/* Main Log Feed */}
                    <div className="glass-panel" style={{ padding: '0', overflow: 'hidden', height: '70vh', display: 'flex', flexDirection: 'column' }}>
                        <div style={{ padding: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'rgba(0,0,0,0.2)', display: 'flex', justifyContent: 'space-between' }}>
                            <h3 style={{ margin: 0, fontSize: '0.9rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>Decisiones en Tiempo Real</h3>
                            <span style={{ fontSize: '0.8rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: 4 }}>
                                <span className="pulse-dot"></span> Online
                            </span>
                        </div>

                        <div className="custom-scrollbar" style={{ flex: 1, overflowY: 'auto', padding: '0' }}>
                            {auditLogs.length === 0 ? (
                                <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
                                    Esperando nuevos eventos del Clusterizer...
                                </div>
                            ) : (
                                auditLogs.map((log, idx) => (
                                    <div
                                        onClick={() => setSelectedLog(log)}
                                        key={idx}
                                        style={{
                                            padding: '0.85rem 1rem',
                                            borderBottom: '1px solid rgba(255,255,255,0.03)',
                                            background: log.decision === 'JOINED_CLUSTER' ? 'rgba(16, 185, 129, 0.02)' : 'transparent',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '1rem',
                                            fontSize: '0.9rem',
                                            cursor: 'pointer',
                                            transition: 'background 0.2s'
                                        }}
                                        className="log-row"
                                    >
                                        {/* Time */}
                                        <div style={{ color: '#64748b', fontSize: '0.75rem', minWidth: '40px' }}>
                                            {new Date(log.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                        </div>

                                        {/* Decision Badge */}
                                        <div style={{ minWidth: '100px' }}>
                                            {log.decision === 'JOINED_CLUSTER' ? (
                                                <span style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#10b981', padding: '2px 8px', borderRadius: 4, fontSize: '0.7rem', fontWeight: 'bold' }}>MATCH</span>
                                            ) : log.decision === 'CANDIDATE' ? (
                                                <span style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', padding: '2px 8px', borderRadius: 4, fontSize: '0.7rem', fontWeight: 'bold' }}>CANDIDATO</span>
                                            ) : (
                                                <span style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', padding: '2px 8px', borderRadius: 4, fontSize: '0.7rem', fontWeight: 'bold' }}>REJECT</span>
                                            )}
                                        </div>

                                        {/* Products Info */}
                                        <div style={{ flex: 1, overflow: 'hidden' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: 2 }}>
                                                <span style={{ color: '#fff', fontWeight: 500 }}>{log.title_a}</span>
                                                <span style={{ color: '#64748b' }}>vs</span>
                                            </div>
                                            <div style={{ color: '#94a3b8', fontSize: '0.8rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                {log.title_b}
                                            </div>
                                        </div>

                                        {/* Scores */}
                                        <div style={{ display: 'flex', gap: '1rem', minWidth: '180px' }}>
                                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                                <div style={{ width: '40px', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: 2, overflow: 'hidden' }}>
                                                    <div style={{ width: `${log.visual_score * 100}%`, height: '100%', background: '#3b82f6' }}></div>
                                                </div>
                                                <span style={{ fontSize: '0.7rem', color: '#64748b', marginTop: 2 }}><Eye size={10} style={{ marginRight: 2 }} /> {Math.round(log.visual_score * 100)}%</span>
                                            </div>
                                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                                <div style={{ width: '40px', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: 2, overflow: 'hidden' }}>
                                                    <div style={{ width: `${log.text_score * 100}%`, height: '100%', background: '#8b5cf6' }}></div>
                                                </div>
                                                <span style={{ fontSize: '0.7rem', color: '#64748b', marginTop: 2 }}><FileText size={10} style={{ marginRight: 2 }} /> {Math.round(log.text_score * 100)}%</span>
                                            </div>
                                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                                <span style={{ color: getScoreColor(log.final_score), fontWeight: 'bold' }}>
                                                    {(log.final_score * 100).toFixed(0)}%
                                                </span>
                                                <span style={{ fontSize: '0.65rem', color: '#64748b' }}>FINAL</span>
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Sidebar Stats */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        <div className="glass-card" style={{ padding: '1.5rem', textAlign: 'center' }}>
                            <h4 style={{ color: '#94a3b8', marginBottom: '0.5rem' }}>Efectividad Reciente</h4>
                            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#10b981' }}>
                                {auditLogs.filter(l => l.decision === 'JOINED_CLUSTER').length}
                            </div>
                            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Matches (últimos 100 eventos)</span>
                        </div>

                        <div className="glass-card" style={{ padding: '1.5rem' }}>
                            <h4 style={{ color: '#fff', fontSize: '0.9rem', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>
                                Leyenda de Métodos
                            </h4>
                            <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.85rem', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#3b82f6' }}></div>
                                    <span><strong>Visual Match:</strong> Foto idéntica (92%+)</span>
                                </li>
                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#8b5cf6' }}></div>
                                    <span><strong>Text Rescue:</strong> Texto idéntico salvó foto distinta.</span>
                                </li>
                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b' }}></div>
                                    <span><strong>Hybrid Score:</strong> Promedio ponderado.</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            )}

            {/* ORPHANS TAB - INVESTIGATOR */}
            {activeTab === 'orphans' && (
                <div>
                    <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', marginBottom: '1rem' }}>
                        <Search size={48} color="#6366f1" style={{ marginBottom: '1rem' }} />
                        <h2>Investigador de Solitarios</h2>
                        <p style={{ color: '#94a3b8', maxWidth: '600px', margin: '0 auto' }}>
                            Estos productos no encontraron pareja. Haz clic en uno para forzar una búsqueda de candidatos profundos.
                        </p>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1rem' }}>
                        {orphans.map(orphan => (
                            <div key={orphan.cluster_id} className="glass-card" style={{ padding: '1rem', position: 'relative' }}>
                                <div style={{ width: '100%', height: '180px', borderRadius: 8, overflow: 'hidden', marginBottom: '1rem', background: '#000' }}>
                                    <img src={orphan.image} alt="" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                                </div>
                                <h4 style={{ fontSize: '0.9rem', marginBottom: '0.5rem', lineHeight: '1.4' }}>{orphan.title}</h4>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: '#94a3b8' }}>
                                    <span>ID: {orphan.product_id}</span>
                                    <span>${orphan.price}</span>
                                </div>
                                <button onClick={() => handleAuditOrphan(orphan)} style={{
                                    width: '100%',
                                    marginTop: '1rem',
                                    padding: '0.5rem',
                                    background: 'rgba(99, 102, 241, 0.1)',
                                    border: '1px solid rgba(99, 102, 241, 0.3)',
                                    color: '#818cf8',
                                    borderRadius: 6,
                                    cursor: 'pointer'
                                }}>
                                    Auditar (Simular)
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* AUDIT MODAL */}
            {selectedLog && (
                <AuditModal log={selectedLog} onClose={() => setSelectedLog(null)} />
            )}

            <style jsx>{`
                .log-row:hover { background: rgba(255,255,255,0.05) !important; }
                .pulse-dot {
                    width: 8px;
                    height: 8px;
                    background: #10b981;
                    border-radius: 50%;
                    box-shadow: 0 0 0 rgba(16, 185, 129, 0.4);
                    animation: pulse 2s infinite;
                }
                @keyframes pulse {
                    0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
                    70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
                    100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
                }
            `}</style>
        </div>
    );
};

export default ClusterLab;
