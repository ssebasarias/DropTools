import React, { useEffect, useState } from 'react';
import { Save, Info, Clock, Mail, Key, Plus, CheckCircle2, XCircle, Play, RefreshCw, FileText, Phone, User, Package } from 'lucide-react';
import { createDropiAccount, fetchDropiAccounts, setDefaultDropiAccount, fetchReporterConfig, updateReporterConfig, startReporterWorkflow, fetchReporterStatus, fetchReporterList } from '../../services/api';
import SubscriptionGate from '../../components/common/SubscriptionGate';
import { getAuthUser } from '../../services/authService';
import { hasTier } from '../../utils/subscription';

const ReporterConfigInner = () => {
    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [creating, setCreating] = useState(false);

    // Reporter status & control
    const [starting, setStarting] = useState(false);
    const [status, setStatus] = useState(null);
    const [statusLoading, setStatusLoading] = useState(false);
    const [reportsList, setReportsList] = useState([]);
    const [reportsLoading, setReportsLoading] = useState(false);
    const [workflowProgress, setWorkflowProgress] = useState(null);

    const [form, setForm] = useState({
        label: 'reporter',
        email: '',
        password: '',
        is_default: false,
        executionTime: '08:00'
    });

    const load = async () => {
        setError('');
        setLoading(true);
        try {
            const list = await fetchDropiAccounts();
            setAccounts(list);
            const cfg = await fetchReporterConfig();
            if (cfg?.executionTime) {
                setForm((prev) => ({ ...prev, executionTime: cfg.executionTime }));
            }
        } catch (e) {
            setError(e.message || 'Error cargando cuentas');
        } finally {
            setLoading(false);
        }
    };

    const loadStatus = async (silent = false) => {
        if (!silent) setStatusLoading(true);
        try {
            const statusData = await fetchReporterStatus();
            setStatus(statusData);
            if (statusData?.workflow_progress) {
                setWorkflowProgress(statusData.workflow_progress);
            }
        } catch (e) {
            console.error('Error cargando estado:', e);
        } finally {
            if (!silent) setStatusLoading(false);
        }
    };

    const loadReportsList = async (silent = false) => {
        if (!silent) setReportsLoading(true);
        try {
            const data = await fetchReporterList(1, 50, 'reportado');
            setReportsList(data.results || []);
        } catch (e) {
            console.error('Error cargando lista de reportes:', e);
        } finally {
            if (!silent) setReportsLoading(false);
        }
    };

    const handleStartWorkflow = async () => {
        setError('');
        setStarting(true);
        try {
            await startReporterWorkflow();
            setTimeout(() => {
                loadStatus(true);
                loadReportsList(true);
            }, 2000);
        } catch (e) {
            setError(e.message || 'Error al iniciar workflow');
        } finally {
            setStarting(false);
        }
    };

    useEffect(() => {
        load();
        loadStatus();
        loadReportsList();
    }, []);

    // Auto-refresh status every 3 seconds when workflow is running
    useEffect(() => {
        const isWorkflowRunning = workflowProgress &&
            ['step1_running', 'step2_running', 'step3_running', 'step1_completed', 'step2_completed'].includes(workflowProgress.status);

        if (isWorkflowRunning) {
            const interval = setInterval(() => {
                loadStatus(true);
                loadReportsList(true); // También actualizar lista de reportes cuando el workflow está corriendo
            }, 3000); // Polling más frecuente cuando está corriendo
            return () => clearInterval(interval);
        } else {
            // Polling normal cuando no está corriendo
            const interval = setInterval(() => {
                loadStatus(true);
            }, 10000);
            return () => clearInterval(interval);
        }
    }, [workflowProgress?.status]);

    // Auto-refresh reports list when status updates
    useEffect(() => {
        if (status?.total_reported > 0) {
            const interval = setInterval(() => {
                loadReportsList(true);
            }, 5000);
            return () => clearInterval(interval);
        }
    }, [status?.total_reported]);

    return (
        <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
            <style>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                .spinning {
                    animation: spin 1s linear infinite;
                }
            `}</style>
            <div style={{ marginBottom: '2rem' }}>
                <h1 className="text-gradient" style={{ fontSize: '2.5rem', margin: 0 }}>Reporter Configuration</h1>
                <p className="text-muted" style={{ marginTop: '0.5rem' }}>Gestiona la generaciÃ³n de reportes de Ã³rdenes sin movimiento.</p>
            </div>

            {/* Primera fila: Instrucciones y Formulario de cuenta */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                {/* Cuadrado de Instrucciones */}
                <div className="glass-card" style={{
                    backgroundColor: 'rgba(99, 102, 241, 0.05)',
                    borderColor: 'rgba(99, 102, 241, 0.2)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '1rem'
                }}>
                    <div style={{ display: 'flex', alignItems: 'start', gap: '1rem' }}>
                        <div style={{
                            padding: '0.75rem',
                            background: 'rgba(99, 102, 241, 0.2)',
                            borderRadius: '12px',
                            flexShrink: 0
                        }}>
                            <Info size={24} style={{ color: 'var(--primary)' }} />
                        </div>
                        <div style={{ flex: 1 }}>
                            <h3 style={{ margin: '0 0 0.5rem 0', color: 'var(--primary)', fontSize: '1.25rem' }}>
                                Instrucciones para Permisos
                            </h3>
                            <div style={{ fontSize: '0.95rem', lineHeight: '1.7', color: 'var(--text-main)' }}>
                                <p style={{ marginBottom: '1rem' }}>
                                    Para garantizar la seguridad de tu cuenta principal y el correcto funcionamiento del reporter,
                                    <strong> crea una cuenta secundaria</strong> en Dropi con permisos restringidos si es posible.
                                </p>
                                <p style={{ marginBottom: '1rem' }}>
                                    Esta cuenta secundaria debe tener acceso a:
                                </p>
                                <ul style={{ marginLeft: '1.5rem', marginBottom: '1rem', color: 'var(--text-muted)' }}>
                                    <li>Visualizar Ã³rdenes</li>
                                    <li>Generar reportes</li>
                                    <li>Acceso de solo lectura recomendado</li>
                                </ul>
                                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                                    El reporter usarÃ¡ estas credenciales para acceder a tu dashboard y generar reportes automÃ¡ticamente.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Cuadrado de Inputs y BotÃ³n Guardar */}
                <div className="glass-card">
                    <h3 style={{ marginBottom: '1.5rem', fontSize: '1.25rem' }}>Guardar Cuenta Secundaria</h3>

                    {error && (
                        <div style={{
                            marginBottom: '1rem',
                            padding: '0.75rem 1rem',
                            background: 'rgba(239,68,68,0.1)',
                            border: '1px solid rgba(239,68,68,0.3)',
                            borderRadius: '8px',
                            color: '#ef4444',
                            fontSize: '0.9rem'
                        }}>
                            {error}
                        </div>
                    )}

                    {loading ? (
                        <p className="text-muted">Cargando cuentas...</p>
                    ) : accounts.length > 0 && (
                        <div style={{ marginBottom: '1.5rem', padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid var(--glass-border)' }}>
                            <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: '0.75rem' }}>Cuentas registradas:</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                {accounts.map((a) => (
                                    <div
                                        key={a.id}
                                        style={{
                                            padding: '0.75rem',
                                            background: 'var(--glass-bg)',
                                            borderRadius: '8px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between',
                                            fontSize: '0.9rem'
                                        }}
                                    >
                                        <div>
                                            <span style={{ fontWeight: 600 }}>{a.label}</span>
                                            {a.is_default && <span style={{ color: 'var(--primary)', marginLeft: '0.5rem', fontSize: '0.8rem' }}>(default)</span>}
                                            <div className="text-muted" style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
                                                {a.email}
                                            </div>
                                        </div>
                                        {!a.is_default && (
                                            <button
                                                type="button"
                                                className="btn-secondary"
                                                style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                                                onClick={async () => {
                                                    await setDefaultDropiAccount(a.id);
                                                    await load();
                                                }}
                                            >
                                                <CheckCircle2 size={14} style={{ marginRight: '0.25rem' }} />
                                                Default
                                            </button>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="form-group">
                        <label className="form-label">Correo ElectrÃ³nico</label>
                        <div style={{ position: 'relative' }}>
                            <Mail size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', zIndex: 1 }} />
                            <input
                                type="email"
                                className="glass-input"
                                style={{ paddingLeft: '38px' }}
                                placeholder="reporter@yourdomain.com"
                                value={form.email}
                                onChange={(e) => setForm({ ...form, email: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label">ContraseÃ±a</label>
                        <div style={{ position: 'relative' }}>
                            <Key size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', zIndex: 1 }} />
                            <input
                                type="password"
                                className="glass-input"
                                style={{ paddingLeft: '38px' }}
                                placeholder="â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢"
                                value={form.password}
                                onChange={(e) => setForm({ ...form, password: e.target.value })}
                            />
                        </div>
                    </div>

                    <button
                        type="button"
                        className="btn-primary"
                        style={{
                            width: '100%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.5rem',
                            opacity: creating ? 0.7 : 1
                        }}
                        disabled={creating || !form.email || !form.password}
                        onClick={async () => {
                            setError('');
                            setCreating(true);
                            try {
                                await createDropiAccount({
                                    label: form.label || 'reporter',
                                    email: form.email,
                                    password: form.password,
                                    is_default: false
                                });
                                setForm({ ...form, email: '', password: '' });
                                await load();
                            } catch (e) {
                                setError(e.message || 'Error guardando');
                            } finally {
                                setCreating(false);
                            }
                        }}
                    >
                        {creating ? (
                            <>
                                <RefreshCw size={18} className="spinning" />
                                Guardando...
                            </>
                        ) : (
                            <>
                                <Save size={18} />
                                Guardar Cuenta
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Segunda fila: BotÃ³n Iniciar y KPI Contador */}
            <div className="glass-card" style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '2rem', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1 }}>
                        <button
                            type="button"
                            className="btn-primary"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                opacity: starting ? 0.7 : 1,
                                padding: '1rem 2rem',
                                fontSize: '1rem'
                            }}
                            disabled={starting}
                            onClick={handleStartWorkflow}
                        >
                            {starting ? (
                                <>
                                    <RefreshCw size={20} className="spinning" />
                                    Iniciando...
                                </>
                            ) : (
                                <>
                                    <Play size={20} />
                                    Iniciar a Reportar
                                </>
                            )}
                        </button>
                    </div>

                    {/* KPI Contador de Reportes del DÃ­a */}
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '1rem',
                        padding: '1rem 1.5rem',
                        background: 'rgba(99,102,241,0.1)',
                        borderRadius: '12px',
                        border: '1px solid rgba(99,102,241,0.2)'
                    }}>
                        <div style={{
                            padding: '0.75rem',
                            background: 'rgba(99,102,241,0.2)',
                            borderRadius: '10px'
                        }}>
                            <FileText size={24} style={{ color: 'var(--primary)' }} />
                        </div>
                        <div>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0, marginBottom: '0.25rem' }}>
                                Reportes Realizados Hoy
                            </p>
                            <h2 style={{
                                fontSize: '2.5rem',
                                margin: 0,
                                fontWeight: 'bold',
                                background: 'linear-gradient(135deg, var(--primary), #4f46e5)',
                                WebkitBackgroundClip: 'text',
                                WebkitTextFillColor: 'transparent'
                            }}>
                                {status?.total_reported || 0}
                            </h2>
                        </div>
                    </div>
                </div>
            </div>

            {/* Panel de Progreso del Workflow */}
            {workflowProgress && (
                <div className="glass-card" style={{ marginBottom: '2rem', border: '2px solid rgba(99,102,241,0.3)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                        <div style={{
                            padding: '0.75rem',
                            background: workflowProgress.status === 'completed' ? 'rgba(16,185,129,0.2)' :
                                workflowProgress.status === 'failed' ? 'rgba(239,68,68,0.2)' :
                                    'rgba(99,102,241,0.2)',
                            borderRadius: '12px'
                        }}>
                            {workflowProgress.status === 'completed' ? (
                                <CheckCircle2 size={24} style={{ color: 'var(--success)' }} />
                            ) : workflowProgress.status === 'failed' ? (
                                <XCircle size={24} style={{ color: 'var(--danger)' }} />
                            ) : (
                                <RefreshCw size={24} className="spinning" style={{ color: 'var(--primary)' }} />
                            )}
                        </div>
                        <div style={{ flex: 1 }}>
                            <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Progreso del Workflow</h3>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0.25rem 0 0 0' }}>
                                {workflowProgress.current_message || 'Iniciando...'}
                            </p>
                        </div>
                    </div>

                    {/* Lista de mensajes de progreso */}
                    {workflowProgress.messages && workflowProgress.messages.length > 0 && (
                        <div style={{
                            marginTop: '1rem',
                            padding: '1rem',
                            background: 'rgba(255,255,255,0.03)',
                            borderRadius: '12px',
                            maxHeight: '200px',
                            overflowY: 'auto'
                        }}>
                            {workflowProgress.messages.map((msg, idx) => (
                                <div key={idx} style={{
                                    padding: '0.5rem 0',
                                    borderBottom: idx < workflowProgress.messages.length - 1 ? '1px solid var(--glass-border)' : 'none',
                                    fontSize: '0.9rem',
                                    color: 'var(--text-main)'
                                }}>
                                    <span style={{ marginRight: '0.5rem', color: 'var(--primary)' }}>•</span>
                                    {msg}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Tercera fila: Panel de Control con Lista de Órdenes */}
            <div className="glass-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <div>
                        <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Panel de Control</h3>
                        <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0.25rem 0 0 0' }}>
                            Vista en tiempo real de las órdenes reportadas exitosamente
                        </p>
                    </div>
                    <button
                        type="button"
                        className="btn-secondary"
                        style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                        onClick={() => {
                            loadStatus();
                            loadReportsList();
                        }}
                    >
                        <RefreshCw size={16} />
                        Actualizar
                    </button>
                </div>

                {statusLoading ? (
                    <div style={{ textAlign: 'center', padding: '2rem' }}>
                        <RefreshCw size={24} className="spinning text-muted" />
                        <p className="text-muted" style={{ marginTop: '0.5rem' }}>Cargando estado...</p>
                    </div>
                ) : reportsList.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        padding: '3rem',
                        background: 'rgba(255,255,255,0.02)',
                        borderRadius: '12px',
                        border: '1px dashed var(--glass-border)'
                    }}>
                        <Package size={48} className="text-muted" style={{ opacity: 0.5, marginBottom: '1rem' }} />
                        <p className="text-muted" style={{ margin: 0 }}>
                            No hay órdenes reportadas aún. Presiona "Iniciar a Reportar" para comenzar.
                        </p>
                    </div>
                ) : (
                    <div style={{
                        display: 'grid',
                        gap: '1rem',
                        maxHeight: '500px',
                        overflowY: 'auto',
                        paddingRight: '0.5rem'
                    }}>
                        {reportsList.map((report) => (
                            <div
                                key={report.id}
                                className="glass-panel"
                                style={{
                                    padding: '1.25rem',
                                    display: 'grid',
                                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                                    gap: '1.5rem',
                                    alignItems: 'start',
                                    transition: 'all 0.2s'
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = 'var(--glass-bg-hover)';
                                    e.currentTarget.style.transform = 'translateY(-2px)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = 'var(--glass-bg)';
                                    e.currentTarget.style.transform = 'translateY(0)';
                                }}
                            >
                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                                        <div style={{
                                            padding: '0.5rem',
                                            background: 'rgba(99,102,241,0.2)',
                                            borderRadius: '8px'
                                        }}>
                                            <FileText size={16} style={{ color: 'var(--primary)' }} />
                                        </div>
                                        <strong style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Número de Guía</strong>
                                    </div>
                                    <div style={{ marginLeft: '2.5rem', fontSize: '1rem', fontWeight: '600', color: 'var(--text-main)' }}>
                                        {report.order_id || 'N/A'}
                                    </div>
                                </div>

                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                                        <div style={{
                                            padding: '0.5rem',
                                            background: 'rgba(236,72,153,0.2)',
                                            borderRadius: '8px'
                                        }}>
                                            <Phone size={16} style={{ color: 'var(--secondary)' }} />
                                        </div>
                                        <strong style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Teléfono</strong>
                                    </div>
                                    <div style={{ marginLeft: '2.5rem', fontSize: '1rem', color: 'var(--text-main)' }}>
                                        {report.order_phone || 'N/A'}
                                    </div>
                                </div>

                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                                        <div style={{
                                            padding: '0.5rem',
                                            background: 'rgba(16,185,129,0.2)',
                                            borderRadius: '8px'
                                        }}>
                                            <User size={16} style={{ color: 'var(--success)' }} />
                                        </div>
                                        <strong style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Cliente</strong>
                                    </div>
                                    <div style={{ marginLeft: '2.5rem', fontSize: '0.95rem', color: 'var(--text-main)' }}>
                                        {report.customer_name || 'N/A'}
                                    </div>
                                </div>

                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                                        <div style={{
                                            padding: '0.5rem',
                                            background: 'rgba(245,158,11,0.2)',
                                            borderRadius: '8px'
                                        }}>
                                            <Clock size={16} style={{ color: 'var(--warning)' }} />
                                        </div>
                                        <strong style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Días sin Movimiento</strong>
                                    </div>
                                    <div style={{ marginLeft: '2.5rem' }}>
                                        <span style={{
                                            fontSize: '1.1rem',
                                            fontWeight: 'bold',
                                            color: (report.days_without_movement || 0) > 7 ? 'var(--danger)' : ((report.days_without_movement || 0) > 3 ? 'var(--warning)' : 'var(--success)')
                                        }}>
                                            {report.days_without_movement || report.days_stuck || 'N/A'} días
                                        </span>
                                    </div>
                                </div>

                                <div style={{
                                    gridColumn: '1 / -1',
                                    paddingTop: '1rem',
                                    borderTop: '1px solid var(--glass-border)',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    fontSize: '0.85rem',
                                    color: 'var(--text-muted)'
                                }}>
                                    <span>Reportado: {new Date(report.updated_at || report.reported_at || Date.now()).toLocaleString()}</span>
                                    <span style={{
                                        padding: '0.25rem 0.75rem',
                                        background: 'rgba(16,185,129,0.15)',
                                        borderRadius: '9999px',
                                        color: 'var(--success)',
                                        fontSize: '0.75rem',
                                        fontWeight: '600'
                                    }}>
                                        ✓ Reportado Exitosamente
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

const ReporterConfig = () => {
    const user = getAuthUser();
    const ok = hasTier(user, 'BRONZE');
    if (!ok) return <SubscriptionGate minTier="BRONZE" title="Reporter (requiere suscripciÃ³n activa)">{null}</SubscriptionGate>;
    return <ReporterConfigInner />;
};

export default ReporterConfig;