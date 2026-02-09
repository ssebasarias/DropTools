import React, { useEffect, useState, useCallback } from 'react';
import { Save, Info, Clock, Mail, Key, CheckCircle2, XCircle, RefreshCw, FileText, Phone, User, Package, Square, BarChart3, Lock, AlertCircle } from 'lucide-react';
import { createDropiAccount, fetchDropiAccounts, setDefaultDropiAccount, fetchReporterConfig, stopReporterProcesses, fetchReporterStatus, fetchReporterList, fetchReporterEnv, fetchReporterSlots, fetchMyReservation, createReservation, deleteReservation, fetchReporterRuns, fetchReporterRunProgress } from '../../services/api';
import SubscriptionGate from '../../components/common/SubscriptionGate';
import { getAuthUser } from '../../services/authService';
import { hasTier } from '../../utils/subscription';
import EmptyState from '../../components/common/EmptyState';
import ErrorAlert from '../../components/common/ErrorAlert';
import SuccessAlert from '../../components/common/SuccessAlert';

const ReporterConfigInner = () => {
    // Función para validar formato de email
    const isValidEmail = (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [creating, setCreating] = useState(false);
    const [showCancelModal, setShowCancelModal] = useState(false);
    const [showSuccessModal, setShowSuccessModal] = useState(false);

    // Reporter status & control
    const [starting, _setStarting] = useState(false);
    const [stoppingProcesses, setStoppingProcesses] = useState(false);
    const [status, setStatus] = useState(null);
    const [statusLoading, setStatusLoading] = useState(false);
    const [reportsList, setReportsList] = useState([]);
    const [_reportsLoading, setReportsLoading] = useState(false);
    const [workflowProgress, setWorkflowProgress] = useState(null);
    const [reporterEnv, setReporterEnv] = useState(null); // { droptools_env, reporter_use_celery, message }

    // Slots & reservations (nuevo sistema por hora)
    const [myReservation, setMyReservation] = useState(null);
    const [reservationSaving, setReservationSaving] = useState(false);
    const [monthlyOrdersEstimate, setMonthlyOrdersEstimate] = useState(0);
    const [lastRunProgress, setLastRunProgress] = useState(null);

    // Clave para localStorage del formulario de Dropi
    const DROPI_FORM_STORAGE_KEY = 'droptools_dropi_form_draft';

    // Función para cargar formulario desde localStorage
    const loadFormFromStorage = () => {
        try {
            const saved = localStorage.getItem(DROPI_FORM_STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                return {
                    label: parsed.label || 'reporter',
                    email: parsed.email || '',
                    password: parsed.password || '',
                    is_default: parsed.is_default || false,
                    executionTime: parsed.executionTime || '08:00'
                };
            }
        } catch (e) {
            console.error('Error cargando formulario desde localStorage:', e);
        }
        return {
            label: 'reporter',
            email: '',
            password: '',
            is_default: false,
            executionTime: '08:00'
        };
    };

    const [form, setForm] = useState(loadFormFromStorage);
    const [proxyAssigned, setProxyAssigned] = useState(null); // Solo lectura: IP asignada (host:port o null)

    const load = useCallback(async () => {
        const STORAGE_KEY = 'droptools_dropi_form_draft';
        setError('');
        setLoading(true);
        try {
            const list = await fetchDropiAccounts();
            setAccounts(Array.isArray(list) ? list : []);
            const cfg = await fetchReporterConfig();
            if (cfg?.executionTime) {
                setForm((prev) => ({ ...prev, executionTime: cfg.executionTime }));
            }
            setProxyAssigned(cfg?.proxy_assigned ?? null);

            // Si no hay cuentas guardadas, restaurar formulario desde localStorage
            if ((Array.isArray(list) ? list : []).length === 0) {
                try {
                    const saved = localStorage.getItem(STORAGE_KEY);
                    if (saved) {
                        const parsed = JSON.parse(saved);
                        if (parsed.email || parsed.password) {
                            setForm((prev) => ({
                                ...prev,
                                email: parsed.email || '',
                                password: parsed.password || '',
                                label: parsed.label || 'reporter'
                            }));
                        }
                    }
                } catch (e) {
                    console.error('Error restaurando formulario desde localStorage:', e);
                }
            } else {
                // Si hay cuentas, limpiar localStorage del formulario
                try {
                    localStorage.removeItem(STORAGE_KEY);
                } catch (e) {
                    console.error('Error limpiando localStorage:', e);
                }
            }
        } catch (e) {
            setError(e.message || 'Error cargando cuentas');
        } finally {
            setLoading(false);
        }
    }, []);

    const loadStatus = useCallback(async (silent = false) => {
        if (!silent) setStatusLoading(true);
        try {
            const statusData = await fetchReporterStatus();
            setStatus(statusData);
            if (statusData?.workflow_progress) {
                setWorkflowProgress(statusData.workflow_progress);
            } else {
                setWorkflowProgress((prev) => prev ?? null);
            }
            if (!silent) setError('');
        } catch (e) {
            console.error('Error cargando estado:', e);
            if (!silent) setError(e.message || 'Error al cargar el estado del reporter');
        } finally {
            if (!silent) setStatusLoading(false);
        }
    }, []);

    const loadReportsList = useCallback(async (silent = false) => {
        if (!silent) setReportsLoading(true);
        try {
            const data = await fetchReporterList(1, 50, 'reportado');
            setReportsList(data.results || []);
        } catch (e) {
            console.error('Error cargando lista de reportes:', e);
            // Always surface errors to user (non-silent only)
            if (!silent) {
                setError(e.message || 'Error al cargar la lista de reportes');
            }
        } finally {
            if (!silent) setReportsLoading(false);
        }
    }, []);

    const handleConfirmReservation = async () => {
        setError('');
        setSuccessMessage('');
        setReservationSaving(true);
        try {
            // Asignación automática: solo enviamos monthly_orders_estimate
            const response = await createReservation({ monthly_orders_estimate: monthlyOrdersEstimate });

            // El backend retorna la reserva con el slot asignado y un mensaje
            const assignedHour = response.slot?.hour_label || `${String(response.slot?.hour ?? '').padStart(2, '0')}:00`;
            const backendMessage = response.message || `¡Reserva confirmada! Tus reportes se ejecutarán automáticamente todos los días a las ${assignedHour}`;

            setSuccessMessage(backendMessage);
            // Mostrar modal en lugar de cargar inmediatamente
            setShowSuccessModal(true);
        } catch (e) {
            setError(e.message || 'No se pudo crear la reserva');
        } finally {
            setReservationSaving(false);
        }
    };

    const handleCancelReservation = async () => {
        setError('');
        setSuccessMessage('');
        try {
            await deleteReservation();
            setMyReservation(null);
        } catch (e) {
            setError(e.message || 'No se pudo cancelar la reserva');
        }
    };

    const handleStopProcesses = async () => {
        setError('');
        setStoppingProcesses(true);
        try {
            const data = await stopReporterProcesses();
            setError('');
            const msg = data.message || `Detenidos: ${data.stopped ?? 0} tarea(s). Cola purgada: ${data.purged ? 'sí' : 'no'}.`;
            setWorkflowProgress(prev => prev
                ? { ...prev, status: 'stopped', current_message: `Detenido. ${msg}`, messages: [...(prev.messages || []), `[Detenido] ${msg}`] }
                : { status: 'stopped', current_message: `Detenido. ${msg}`, messages: [`[Detenido] ${msg}`] }
            );
            loadStatus(true);
            loadReportsList(true);
        } catch (e) {
            setError(e.message || 'Error al detener procesos');
        } finally {
            setStoppingProcesses(false);
        }
    };

    const loadReporterEnv = useCallback(async () => {
        try {
            const envData = await fetchReporterEnv();
            setReporterEnv(envData);
        } catch {
            setReporterEnv({ droptools_env: 'production', reporter_use_celery: true });
        }
    }, []);

    const loadRunsAndProgress = useCallback(async () => {
        try {
            // 1. Ver si hay runs hoy o recientes
            const runsData = await fetchReporterRuns();
            if (runsData && runsData.results && runsData.results.length > 0) {
                // Tomar el más reciente
                const lastRun = runsData.results[0];
                // 2. Cargar progreso detallado
                const progress = await fetchReporterRunProgress(lastRun.id);
                setLastRunProgress(progress);
            } else {
                setLastRunProgress(null);
            }
        } catch (e) {
            console.error('Error cargando runs/progreso:', e);
            // No mostrar error en UI, es info secundaria
        }
    }, []);

    const loadMyReservation = useCallback(async () => {
        try {
            const data = await fetchMyReservation();
            setMyReservation(data ?? null);
            if (data != null && typeof data.monthly_orders_estimate === 'number') {
                setMonthlyOrdersEstimate(data.monthly_orders_estimate);
            }
        } catch (e) {
            console.error('Error cargando reserva:', e);
            setMyReservation(null);
        }
    }, []);

    // Guardar formulario en localStorage cada vez que cambie (solo si no hay cuentas guardadas)
    useEffect(() => {
        // Solo guardar si no hay cuentas ya guardadas (para no interferir con el flujo normal)
        if (accounts.length === 0 && (form.email || form.password)) {
            try {
                localStorage.setItem(DROPI_FORM_STORAGE_KEY, JSON.stringify({
                    email: form.email,
                    password: form.password,
                    label: form.label,
                    is_default: form.is_default,
                    executionTime: form.executionTime
                }));
            } catch (e) {
                console.error('Error guardando formulario en localStorage:', e);
            }
        }
    }, [form, accounts.length]);

    // Carga inicial: cada llamada es independiente para que un error (ej. lista reportes) no bloquee reserva
    useEffect(() => {
        load().catch(() => { });
        loadStatus().catch(() => { });
        loadReportsList().catch(() => { });
        loadReporterEnv().catch(() => { });
        loadMyReservation().catch(() => { });
        loadRunsAndProgress().catch(() => { });
    }, [load, loadStatus, loadReportsList, loadReporterEnv, loadMyReservation, loadRunsAndProgress]);

    // Auto-refresh solo cuando el workflow está corriendo (menos frecuente en reposo para evitar parpadeos)
    useEffect(() => {
        const isWorkflowRunning = workflowProgress &&
            ['step1_running', 'step2_running', 'step3_running', 'step1_completed', 'step2_completed'].includes(workflowProgress.status);
        const isStep3 = workflowProgress?.status === 'step3_running';

        const ms = isStep3 ? 3000 : (isWorkflowRunning ? 5000 : 30000); // Idle: 30s (antes 10s), running: 5s, step3: 3s
        const interval = setInterval(() => {
            loadStatus(true);
            if (isWorkflowRunning) loadReportsList(true);
        }, ms);

        return () => clearInterval(interval);
    }, [workflowProgress?.status, loadStatus, loadReportsList]);

    // Auto-refresh lista de reportes solo cuando hay reportes y cada 10s (no 5s para reducir parpadeo)
    useEffect(() => {
        if (status?.total_reported > 0) {
            const interval = setInterval(() => loadReportsList(true), 10000);
            return () => clearInterval(interval);
        }
    }, [status?.total_reported, loadReportsList]);

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
                
                /* Animación fade-in con movimiento hacia arriba */
                @keyframes fadeInUp {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                /* Animación slide-in desde la izquierda */
                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateX(-10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateX(0);
                    }
                }
                
                /* Animación fade-in */
                @keyframes fadeIn {
                    from {
                        opacity: 0;
                    }
                    to {
                        opacity: 1;
                    }
                }
            `}</style>
            <div style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                    <h1 className="text-gradient" style={{ fontSize: '2.5rem', margin: 0 }}>Reporter Configuration</h1>
                    {reporterEnv && (
                        <span
                            title={reporterEnv.message || (reporterEnv.run_mode === 'development_docker' ? 'Reporter vía Celery en Docker (pruebas)' : reporterEnv.droptools_env === 'development' ? 'Reporter en proceso (navegador visible)' : 'Reporter vía Celery (producción)')}
                            style={{
                                padding: '0.35rem 0.75rem',
                                borderRadius: '9999px',
                                fontSize: '0.8rem',
                                fontWeight: 600,
                                backgroundColor: reporterEnv.run_mode === 'development_docker' ? 'rgba(245, 158, 11, 0.2)' : reporterEnv.droptools_env === 'development' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(99, 102, 241, 0.2)',
                                color: reporterEnv.run_mode === 'development_docker' ? 'var(--warning)' : reporterEnv.droptools_env === 'development' ? 'var(--success)' : 'var(--primary)',
                                border: `1px solid ${reporterEnv.run_mode === 'development_docker' ? 'var(--warning)' : reporterEnv.droptools_env === 'development' ? 'var(--success)' : 'var(--primary)'}`,
                            }}
                        >
                            {reporterEnv.run_mode === 'development_docker' ? 'Modo desarrollo (Docker)' : reporterEnv.droptools_env === 'development' ? 'Modo desarrollo' : 'Modo producción'}
                        </span>
                    )}
                </div>
                <p className="text-muted" style={{ marginTop: '0.5rem' }}>Gestiona la generación de reportes de órdenes sin movimiento.</p>
                {proxyAssigned && (
                    <p className="text-muted" style={{ marginTop: '0.25rem', fontSize: '0.9rem' }}>IP asignada: {proxyAssigned} (solo lectura)</p>
                )}
            </div>

            {/* Pantalla con reserva: Panel 1 — Información de cuenta */}
            {myReservation && (
                <div
                    className="glass-card"
                    style={{
                        marginBottom: '2rem',
                        border: '2px solid rgba(16,185,129,0.25)',
                        animation: 'fadeInUp 0.5s ease-out'
                    }}
                >
                    <h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Mail size={22} style={{ color: 'var(--primary)' }} />
                        Información de cuenta
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                        <div>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0 0 0.25rem 0' }}>Email Dropi</p>
                            <p style={{ margin: 0, fontWeight: 600 }}>{accounts.length > 0 ? (accounts.find(a => a.is_default)?.email || accounts[0]?.email) || 'Cuenta vinculada' : 'Cuenta vinculada'}</p>
                        </div>
                        <div>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0 0 0.25rem 0' }}>Hora asignada</p>
                            <p style={{ margin: 0, fontWeight: 600 }}>{myReservation.slot?.hour_label ?? `${String(myReservation.slot?.hour ?? '').padStart(2, '0')}:00`}</p>
                        </div>
                        <div>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0 0 0.25rem 0' }}>Estado de suscripción</p>
                            <p style={{ margin: 0, fontWeight: 600 }}>{getAuthUser() ? (hasTier(getAuthUser(), 'BRONZE') ? 'Activa' : 'Revisar') : '—'}</p>
                        </div>
                        <div>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0 0 0.25rem 0' }}>IP asignada</p>
                            <p style={{ margin: 0, fontWeight: 600 }}>{proxyAssigned || 'Sin proxy asignado'}</p>
                        </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginTop: '1rem' }}>
                        <p style={{ margin: 0, fontSize: '1rem', color: 'var(--success)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <CheckCircle2 size={20} style={{ color: 'var(--success)' }} />
                            ¡Todo listo! Tu reporte se ejecutará automáticamente todos los días a las {myReservation.slot?.hour_label ?? `${String(myReservation.slot?.hour ?? '').padStart(2, '0')}:00`} 🎉
                        </p>
                        <button
                            type="button"
                            onClick={() => setShowCancelModal(true)}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.6rem 1.25rem',
                                borderRadius: '12px',
                                fontWeight: 500,
                                background: 'rgba(239, 68, 68, 0.12)',
                                border: '1px solid rgba(239, 68, 68, 0.35)',
                                color: 'var(--danger)',
                                transition: 'all 0.2s',
                                boxShadow: '0 2px 8px rgba(239, 68, 68, 0.15)'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
                                e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.5)';
                                e.currentTarget.style.transform = 'translateY(-1px)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.12)';
                                e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.35)';
                                e.currentTarget.style.transform = 'translateY(0)';
                            }}
                        >
                            Cancelar reserva
                        </button>
                    </div>
                </div>
            )}

            {/* Pantalla inicial (solo sin reserva): Instrucciones y Formulario de cuenta */}
            {!myReservation && (
                <>
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
                                            <li>Visualizar órdenes</li>
                                            <li>Generar reportes</li>
                                            <li>Acceso de solo lectura recomendado</li>
                                        </ul>
                                        <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                                            El reporter usará estas credenciales para acceder a tu dashboard y generar reportes automáticamente.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Cuadrado de Inputs y Botón Guardar */}
                        <div className="glass-card">
                            <h3 style={{ marginBottom: '1.5rem', fontSize: '1.25rem' }}>Guardar Cuenta Secundaria</h3>

                            <ErrorAlert error={error} onClose={() => setError('')} />
                            <SuccessAlert message={successMessage} onClose={() => setSuccessMessage('')} />

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
                                <label className="form-label">Correo Electrónico</label>
                                <div style={{ position: 'relative' }}>
                                    <Mail size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', zIndex: 1 }} />
                                    <input
                                        type="email"
                                        className="glass-input"
                                        style={{
                                            paddingLeft: '38px',
                                            opacity: accounts.length > 0 ? 0.6 : 1,
                                            borderColor: form.email && !isValidEmail(form.email) ? 'var(--danger)' : 'var(--glass-border)'
                                        }}
                                        placeholder="reporter@yourdomain.com"
                                        value={form.email}
                                        onChange={(e) => {
                                            const email = e.target.value;
                                            setForm({ ...form, email });

                                            // Validar formato de email
                                            if (email && !isValidEmail(email)) {
                                                setError('Por favor ingresa un email válido');
                                            } else {
                                                setError('');
                                            }
                                        }}
                                        disabled={accounts.length > 0}
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label className="form-label">Contraseña</label>
                                <div style={{ position: 'relative' }}>
                                    <Key size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', zIndex: 1 }} />
                                    <input
                                        type="password"
                                        className="glass-input"
                                        style={{ paddingLeft: '38px', opacity: accounts.length > 0 ? 0.6 : 1 }}
                                        placeholder={accounts.length > 0 ? "••••••••• (Oculto)" : "•••••••••"}
                                        value={form.password}
                                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                                        disabled={accounts.length > 0}
                                    />
                                </div>
                            </div>

                            {accounts.length > 0 && (
                                <div style={{ marginBottom: '1rem', padding: '0.75rem', background: 'rgba(234, 179, 8, 0.1)', borderRadius: '8px', border: '1px solid rgba(234, 179, 8, 0.2)', color: '#fbbf24', fontSize: '0.9rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                    <Info size={16} />
                                    <span>Ya tienes una cuenta vinculada. Para cambiarla, contacta soporte o usa el botón de editar (próximamente).</span>
                                </div>
                            )}

                            <button
                                type="button"
                                className="btn-primary"
                                style={{
                                    width: '100%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '0.5rem',
                                    opacity: (creating || accounts.length > 0) ? 0.5 : 1,
                                    cursor: (creating || accounts.length > 0) ? 'not-allowed' : 'pointer'
                                }}
                                disabled={creating || !form.email || !form.password || accounts.length > 0}
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
                                        // Limpiar formulario y localStorage después de guardar exitosamente
                                        const clearedForm = { ...form, email: '', password: '' };
                                        setForm(clearedForm);
                                        try {
                                            localStorage.removeItem(DROPI_FORM_STORAGE_KEY);
                                        } catch (e) {
                                            console.error('Error limpiando localStorage:', e);
                                        }
                                        setSuccessMessage('¡Cuenta guardada exitosamente!');
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
                                ) : accounts.length > 0 ? (
                                    <>
                                        <CheckCircle2 size={18} />
                                        Cuenta Vinculada
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

                    {/* Configuración de reportes automáticos (asignación automática de hora) */}
                    <div className="glass-card" style={{ marginBottom: '2rem' }}>
                        <h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Clock size={22} style={{ color: 'var(--primary)' }} />
                            Configuración de Reportes Automáticos
                        </h3>
                        <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '1.5rem', lineHeight: '1.6' }}>
                            ⏰ <strong>Nuestro sistema asignará automáticamente la mejor hora disponible para tus reportes.</strong><br />
                            Solo necesitamos saber cuántas órdenes aproximadas manejas al mes para optimizar el proceso.
                        </p>

                        <ErrorAlert error={error} onClose={() => setError('')} />
                        <SuccessAlert message={successMessage} onClose={() => setSuccessMessage('')} />

                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: '1rem' }}>
                            <div style={{ flex: '1 1 250px' }}>
                                <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                                    <Package size={16} style={{ color: 'var(--primary)' }} />
                                    ¿Cuántas órdenes aproximadas tienes al mes?
                                </label>
                                <p className="text-muted" style={{ fontSize: '0.8rem', margin: '0.25rem 0 0.5rem 0' }}>
                                    Esto nos ayuda a asignar la mejor hora para que tu reporte termine a tiempo 🚀
                                </p>
                                <input
                                    type="number"
                                    min={0}
                                    max={50000}
                                    className="glass-input"
                                    value={monthlyOrdersEstimate || ''}
                                    onChange={(e) => {
                                        const value = parseInt(e.target.value, 10) || 0;
                                        // Validar rango
                                        if (value < 0) {
                                            setMonthlyOrdersEstimate(0);
                                        } else if (value > 50000) {
                                            setMonthlyOrdersEstimate(50000);
                                            // Mostrar mensaje temporal
                                            setError('El máximo de órdenes mensuales es 50,000. Si tienes más, contacta soporte.');
                                            setTimeout(() => setError(''), 3000);
                                        } else {
                                            setMonthlyOrdersEstimate(value);
                                        }
                                    }}
                                    placeholder="Ej. 500"
                                    style={{
                                        width: '100%',
                                        maxWidth: '200px',
                                        borderColor: monthlyOrdersEstimate > 50000 ? 'var(--danger)' : 'var(--glass-border)',
                                        transition: 'border-color 0.3s ease'
                                    }}
                                />
                                {/* Indicador de volumen */}
                                {monthlyOrdersEstimate > 0 && (
                                    <div style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            marginBottom: '0.25rem',
                                            color: 'var(--text-muted)'
                                        }}>
                                            <span>Volumen estimado:</span>
                                            <span style={{
                                                fontWeight: 600,
                                                color: monthlyOrdersEstimate <= 2000 ? 'var(--success)' :
                                                    monthlyOrdersEstimate <= 5000 ? 'var(--warning)' :
                                                        'var(--primary)'
                                            }}>
                                                {monthlyOrdersEstimate <= 2000 ? '🟢 Bajo (peso 1)' :
                                                    monthlyOrdersEstimate <= 5000 ? '🟡 Medio (peso 2)' :
                                                        '🔵 Alto (peso 3)'}
                                            </span>
                                        </div>
                                        <div style={{
                                            height: '4px',
                                            background: 'rgba(255,255,255,0.1)',
                                            borderRadius: '2px',
                                            overflow: 'hidden'
                                        }}>
                                            <div style={{
                                                height: '100%',
                                                width: `${Math.min((monthlyOrdersEstimate / 10000) * 100, 100)}%`,
                                                background: monthlyOrdersEstimate <= 2000 ? 'var(--success)' :
                                                    monthlyOrdersEstimate <= 5000 ? 'var(--warning)' :
                                                        'var(--primary)',
                                                transition: 'width 0.3s ease, background 0.3s ease',
                                                borderRadius: '2px'
                                            }}></div>
                                        </div>
                                    </div>
                                )}
                            </div>
                            <button
                                type="button"
                                className="btn-primary"
                                disabled={!monthlyOrdersEstimate || monthlyOrdersEstimate <= 0 || reservationSaving}
                                onClick={handleConfirmReservation}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    opacity: (!monthlyOrdersEstimate || monthlyOrdersEstimate <= 0) ? 0.5 : 1,
                                    cursor: (!monthlyOrdersEstimate || monthlyOrdersEstimate <= 0) ? 'not-allowed' : 'pointer'
                                }}
                                title={!monthlyOrdersEstimate || monthlyOrdersEstimate <= 0 ? 'Ingresa la cantidad de órdenes mensuales' : 'Confirmar y asignar hora automáticamente'}
                            >
                                {reservationSaving ? <RefreshCw size={18} className="spinning" /> : <CheckCircle2 size={18} />}
                                {reservationSaving ? 'Asignando...' : 'Confirmar Configuración'}
                            </button>
                        </div>

                        {/* Info adicional */}
                        <div style={{
                            marginTop: '1.5rem',
                            padding: '1rem',
                            background: 'rgba(99, 102, 241, 0.1)',
                            borderRadius: '12px',
                            border: '1px solid rgba(99, 102, 241, 0.2)',
                            display: 'flex',
                            gap: '0.75rem',
                            alignItems: 'start'
                        }}>
                            <Info size={20} style={{ color: 'var(--primary)', flexShrink: 0, marginTop: '2px' }} />
                            <div style={{ fontSize: '0.9rem', lineHeight: '1.6', color: 'var(--text-main)' }}>
                                <strong>¿Cómo funciona?</strong><br />
                                Nuestro sistema analizará la carga actual y asignará automáticamente la mejor hora disponible
                                (entre 6:00 AM y 6:00 PM) para ejecutar tus reportes. Esto garantiza un rendimiento óptimo
                                y evita saturación del sistema. 🎯
                            </div>
                        </div>
                    </div>
                </>
            )}

            {/* Tu progreso (solo con reserva) */}
            {myReservation && (
                <>
                    {/* Tu ejecución de hoy / último progreso */}
                    {lastRunProgress && (
                        <div className="glass-card" style={{ marginBottom: '2rem', border: '2px solid rgba(99,102,241,0.25)' }}>
                            <h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <BarChart3 size={22} style={{ color: 'var(--primary)' }} />
                                Tu ejecución
                            </h3>
                            <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '1rem' }}>
                                Programada: {lastRunProgress.scheduled_at ? new Date(lastRunProgress.scheduled_at).toLocaleString('es-CO') : '—'} · Estado: {lastRunProgress.run_status}
                            </p>
                            {lastRunProgress.users && lastRunProgress.users.length > 0 && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                    {(lastRunProgress.users || []).map((u, idx) => (
                                        <div key={idx} style={{
                                            padding: '0.75rem 1rem',
                                            background: 'rgba(255,255,255,0.03)',
                                            borderRadius: '10px',
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            flexWrap: 'wrap',
                                            gap: '0.5rem'
                                        }}>
                                            <span>{u.username ?? `Usuario ${u.user_id}`}</span>
                                            <span className="text-muted" style={{ fontSize: '0.9rem' }}>
                                                Descarga: {u.download_compare_status} · Rangos: {u.ranges_completed ?? 0}/{u.total_ranges ?? 0}
                                                {u.total_pending_orders != null && u.total_pending_orders > 0 && ` (${u.total_pending_orders} órdenes pendientes)`}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Tu progreso — KPIs */}
                    <div className="glass-card" style={{ marginBottom: '2rem', animation: 'fadeInUp 0.6s ease-out' }}>
                        <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', color: 'var(--text-main)' }}>Tu progreso</h3>

                        {/* En esta ejecución: solo cuando hay workflow activo */}
                        {workflowProgress && ['step1_running', 'step2_running', 'step3_running', 'step1_completed', 'step2_completed'].includes(workflowProgress.status) && (
                            <div style={{
                                padding: '1rem 1.25rem',
                                background: 'rgba(99, 102, 241, 0.08)',
                                borderRadius: '12px',
                                border: '1px solid rgba(99, 102, 241, 0.25)',
                                marginBottom: '1rem'
                            }}>
                                <p className="text-muted" style={{ fontSize: '0.8rem', margin: 0, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <RefreshCw size={14} className="spinning" style={{ color: 'var(--primary)' }} />
                                    En esta ejecución
                                </p>
                                <p style={{ fontSize: '1rem', margin: 0, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
                                    {workflowProgress.current_message || 'Procesando…'}
                                </p>
                                {(() => {
                                    const messages = workflowProgress.messages || [];
                                    const analizadasMsg = messages.find(m => typeof m === 'string' && m.includes('Órdenes totales analizadas'));
                                    const match = analizadasMsg ? analizadasMsg.match(/Órdenes totales analizadas:\s*(\d+).*Sin movimiento:\s*(\d+)/) : null;
                                    let totalAnalizadas = match ? match[1] : null;
                                    let sinMovimiento = match ? match[2] : null;
                                    if (sinMovimiento == null) {
                                        const oldMsg = messages.find(m => typeof m === 'string' && m.includes('Detectadas') && m.includes('órdenes'));
                                        const oldMatch = oldMsg ? oldMsg.match(/Detectadas\s+(\d+)\s+órdenes/) : null;
                                        if (oldMatch) sinMovimiento = oldMatch[1];
                                    }
                                    const hasRunUsers = lastRunProgress?.users && lastRunProgress.users.length > 0;
                                    return (totalAnalizadas != null || sinMovimiento != null || hasRunUsers) ? (
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginTop: '0.75rem', fontSize: '0.9rem', alignItems: 'center' }}>
                                            {totalAnalizadas != null && (
                                                <span style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                                                    <span style={{ color: 'var(--text-muted)' }}>Órdenes totales analizadas:</span>
                                                    <strong style={{ color: 'var(--primary)' }}>{totalAnalizadas}</strong>
                                                </span>
                                            )}
                                            {sinMovimiento != null && (
                                                <span style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                                                    <span style={{ color: 'var(--text-muted)' }}>Órdenes sin movimiento:</span>
                                                    <strong style={{ color: 'var(--warning)' }}>{sinMovimiento}</strong>
                                                </span>
                                            )}
                                            {hasRunUsers && (lastRunProgress.users || []).map((u, idx) => (
                                                <span key={idx} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                                    <span style={{ color: 'var(--text-muted)' }}>Pendientes:</span>
                                                    <strong style={{ color: 'var(--warning)' }}>{u.total_pending_orders ?? 0}</strong>
                                                    <span style={{ color: 'var(--text-muted)' }}>· Reportadas en este run:</span>
                                                    <strong style={{ color: 'var(--success)' }}>{u.ranges_completed ?? 0}</strong>
                                                    <span style={{ color: 'var(--text-muted)' }}> de {u.total_ranges ?? 0}</span>
                                                </span>
                                            ))}
                                        </div>
                                    ) : null;
                                })()}
                            </div>
                        )}

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '1rem', marginBottom: '0.5rem' }}>
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                padding: '1rem 1.25rem',
                                background: 'rgba(99,102,241,0.1)',
                                borderRadius: '12px',
                                border: '1px solid rgba(99,102,241,0.2)'
                            }}>
                                <div style={{ padding: '0.6rem', background: 'rgba(99,102,241,0.2)', borderRadius: '10px' }}>
                                    <FileText size={22} style={{ color: 'var(--primary)' }} />
                                </div>
                                <div>
                                    <p className="text-muted" style={{ fontSize: '0.8rem', margin: 0, marginBottom: '0.2rem' }} title="Contador en vivo: aumenta a medida que el bot va reportando hoy.">Hoy</p>
                                    <p style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold', color: 'var(--primary)' }}>
                                        {(() => {
                                            const fromDb = status?.total_reported ?? 0;
                                            if (workflowProgress?.status === 'step3_running' && lastRunProgress?.users?.length) {
                                                const fromRun = (lastRunProgress.users || []).reduce((s, u) => s + (u.ranges_completed ?? 0), 0);
                                                return Math.max(fromDb, fromRun);
                                            }
                                            return fromDb;
                                        })()}
                                    </p>
                                </div>
                            </div>
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                padding: '1rem 1.25rem',
                                background: 'rgba(16,185,129,0.08)',
                                borderRadius: '12px',
                                border: '1px solid rgba(16,185,129,0.2)'
                            }}>
                                <div style={{ padding: '0.6rem', background: 'rgba(16,185,129,0.2)', borderRadius: '10px' }}>
                                    <BarChart3 size={22} style={{ color: 'var(--success)' }} />
                                </div>
                                <div>
                                    <p className="text-muted" style={{ fontSize: '0.8rem', margin: 0, marginBottom: '0.2rem' }} title="Total de órdenes reportadas desde el día 1 del mes (base de datos).">Este mes</p>
                                    <p style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold', color: 'var(--success)' }}>
                                        {status?.total_reported_month != null
                                            ? status.total_reported_month
                                            : (() => {
                                                const list = reportsList || [];
                                                const now = new Date();
                                                return list.filter(r => {
                                                    const d = r.updated_at || r.reported_at;
                                                    if (!d) return false;
                                                    const dt = new Date(d);
                                                    return dt.getMonth() === now.getMonth() && dt.getFullYear() === now.getFullYear();
                                                }).length;
                                            })()}
                                    </p>
                                </div>
                            </div>
                            {(status?.total_pending != null && status.total_pending > 0) && (
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.75rem',
                                    padding: '1rem 1.25rem',
                                    background: 'rgba(245,158,11,0.08)',
                                    borderRadius: '12px',
                                    border: '1px solid rgba(245,158,11,0.2)'
                                }}>
                                    <div style={{ padding: '0.6rem', background: 'rgba(245,158,11,0.2)', borderRadius: '10px' }}>
                                        <Clock size={22} style={{ color: 'var(--warning)' }} />
                                    </div>
                                    <div>
                                        <p className="text-muted" style={{ fontSize: '0.8rem', margin: 0, marginBottom: '0.2rem' }} title="Órdenes aún no reportadas (pendientes de procesar o en espera).">Pendientes</p>
                                        <p style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold', color: 'var(--warning)' }}>
                                            {status.total_pending}
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                        <p className="text-muted" style={{ fontSize: '0.75rem', margin: 0, marginBottom: '1rem', lineHeight: 1.4 }}>
                            Hoy = contador en vivo que sube mientras el bot reporta. Este mes = total desde el día 1 del mes (base de datos).
                        </p>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '1rem', flexWrap: 'wrap' }}>
                            <button
                                type="button"
                                onClick={() => { loadMyReservation(); loadRunsAndProgress(); loadStatus(); loadReportsList(); }}
                                style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0.6rem 1.25rem',
                                    borderRadius: '12px',
                                    fontWeight: 500,
                                    background: 'rgba(99, 102, 241, 0.12)',
                                    border: '1px solid rgba(99, 102, 241, 0.35)',
                                    color: 'var(--primary)',
                                    transition: 'all 0.2s',
                                    boxShadow: '0 2px 8px rgba(99, 102, 241, 0.15)'
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = 'rgba(99, 102, 241, 0.22)';
                                    e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.5)';
                                    e.currentTarget.style.transform = 'translateY(-1px)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = 'rgba(99, 102, 241, 0.12)';
                                    e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.35)';
                                    e.currentTarget.style.transform = 'translateY(0)';
                                }}
                            >
                                <RefreshCw size={16} />
                                Actualizar
                            </button>
                        </div>
                    </div>

                    {/* Estado del reporte (progreso dinámico) */}
                    {workflowProgress && (
                        <div className="glass-card" style={{ marginBottom: '2rem', border: '2px solid rgba(99,102,241,0.3)', animation: 'fadeInUp 0.7s ease-out' }}>
                            <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', color: 'var(--text-main)' }}>Estado del reporte</h3>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1, minWidth: 0 }}>
                                    <div style={{
                                        padding: '0.75rem',
                                        background: workflowProgress.status === 'completed' ? 'rgba(16,185,129,0.2)' :
                                            workflowProgress.status === 'stopped' || (workflowProgress.status === 'failed' && workflowProgress.current_message && workflowProgress.current_message.includes('detenido')) ? 'rgba(245,158,11,0.2)' :
                                                workflowProgress.status === 'failed' ? 'rgba(239,68,68,0.2)' :
                                                    'rgba(99,102,241,0.2)',
                                        borderRadius: '12px'
                                    }}>
                                        {workflowProgress.status === 'completed' ? (
                                            <CheckCircle2 size={24} style={{ color: 'var(--success)' }} />
                                        ) : workflowProgress.status === 'stopped' || (workflowProgress.status === 'failed' && workflowProgress.current_message && workflowProgress.current_message.includes('detenido')) ? (
                                            <Square size={24} style={{ color: 'var(--warning)' }} />
                                        ) : workflowProgress.status === 'failed' ? (
                                            <XCircle size={24} style={{ color: 'var(--danger)' }} />
                                        ) : (
                                            <RefreshCw size={24} className="spinning" style={{ color: 'var(--primary)' }} />
                                        )}
                                    </div>
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Progreso del Workflow</h3>
                                        <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0.25rem 0 0 0' }}>
                                            {(workflowProgress.status === 'stopped' || (workflowProgress.status === 'failed' && workflowProgress.current_message && workflowProgress.current_message.includes('detenido')))
                                                ? 'Detenido. No hay procesos en ejecución.'
                                                : (workflowProgress.current_message || 'Iniciando...')}
                                        </p>
                                    </div>
                                </div>
                                {(reporterEnv?.run_mode === 'development' || reporterEnv?.run_mode === 'development_docker') && (
                                    <button
                                        type="button"
                                        className="btn-secondary"
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            opacity: stoppingProcesses ? 0.7 : 1,
                                            borderColor: 'var(--danger)',
                                            color: 'var(--danger)',
                                            flexShrink: 0
                                        }}
                                        disabled={stoppingProcesses || starting}
                                        onClick={handleStopProcesses}
                                        title="Detener todas las tareas del reporter y vaciar la cola. Verifica que no quede nada ejecutándose."
                                    >
                                        {stoppingProcesses ? (
                                            <>
                                                <RefreshCw size={16} className="spinning" />
                                                Deteniendo...
                                            </>
                                        ) : (
                                            <>
                                                <Square size={16} />
                                                Detener procesos
                                            </>
                                        )}
                                    </button>
                                )}
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
                                    {(workflowProgress.messages || []).map((msg, idx) => (
                                        <div key={idx} style={{
                                            padding: '0.5rem 0',
                                            borderBottom: idx < (workflowProgress.messages || []).length - 1 ? '1px solid var(--glass-border)' : 'none',
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

                    {/* Tus órdenes reportadas */}
                    <div className="glass-card" style={{ animation: 'fadeInUp 0.8s ease-out' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <div>
                                <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Tus órdenes reportadas</h3>
                                <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0.25rem 0 0 0' }}>
                                    Guía, teléfono, cliente y producto de cada orden reportada
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={() => { loadStatus(); loadReportsList(); }}
                                style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0.6rem 1.25rem',
                                    borderRadius: '12px',
                                    fontWeight: 500,
                                    background: 'rgba(99, 102, 241, 0.12)',
                                    border: '1px solid rgba(99, 102, 241, 0.35)',
                                    color: 'var(--primary)',
                                    transition: 'all 0.2s',
                                    boxShadow: '0 2px 8px rgba(99, 102, 241, 0.15)'
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = 'rgba(99, 102, 241, 0.22)';
                                    e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.5)';
                                    e.currentTarget.style.transform = 'translateY(-1px)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = 'rgba(99, 102, 241, 0.12)';
                                    e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.35)';
                                    e.currentTarget.style.transform = 'translateY(0)';
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
                        ) : (reportsList || []).length === 0 ? (
                            <EmptyState
                                icon={Package}
                                title="No hay reportes por el momento"
                                description="Revisa después de tu hora asignada. Estaremos reportando automáticamente tus órdenes sin movimiento 📦"
                            />
                        ) : (
                            <div style={{
                                display: 'grid',
                                gap: '1rem',
                                maxHeight: '500px',
                                overflowY: 'auto',
                                paddingRight: '0.5rem'
                            }}>
                                {(reportsList || []).map((report, idx) => (
                                    <div
                                        key={report?.id ?? report?.updated_at ?? idx}
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
                                                <strong style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Nombre cliente</strong>
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
                                                    <Package size={16} style={{ color: 'var(--warning)' }} />
                                                </div>
                                                <strong style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Producto</strong>
                                            </div>
                                            <div style={{ marginLeft: '2.5rem', fontSize: '0.95rem', color: 'var(--text-main)' }}>
                                                {report.product_name || 'N/A'}
                                            </div>
                                        </div>

                                        <div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                                                <div style={{
                                                    padding: '0.5rem',
                                                    background: 'rgba(156,163,175,0.2)',
                                                    borderRadius: '8px'
                                                }}>
                                                    <Clock size={16} style={{ color: 'var(--text-muted)' }} />
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
                </>
            )}

            {/* Modal de confirmación para cancelar reserva */}
            {showCancelModal && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(0,0,0,0.7)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 9999,
                    animation: 'fadeIn 0.2s ease-out'
                }}>
                    <div className="glass-card" style={{
                        maxWidth: '500px',
                        margin: '1rem',
                        animation: 'slideIn 0.3s ease-out'
                    }}>
                        <h3 style={{ marginBottom: '1rem', fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <AlertCircle size={24} style={{ color: 'var(--warning)' }} />
                            ¿Cancelar reserva?
                        </h3>
                        <p className="text-muted" style={{ marginBottom: '1.5rem', lineHeight: '1.6' }}>
                            Si cancelas tu reserva, perderás tu hora asignada y tendrás que configurar todo nuevamente.
                            Los reportes automáticos se detendrán hasta que reserves una nueva hora.
                        </p>
                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button
                                type="button"
                                className="btn-secondary"
                                onClick={() => setShowCancelModal(false)}
                            >
                                No, mantener reserva
                            </button>
                            <button
                                type="button"
                                className="btn-primary"
                                style={{
                                    background: 'var(--danger)',
                                    borderColor: 'var(--danger)'
                                }}
                                onClick={async () => {
                                    setShowCancelModal(false);
                                    await handleCancelReservation();
                                }}
                            >
                                Sí, cancelar reserva
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal de Éxito al Confirmar Reserva */}
            {showSuccessModal && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 10000,
                    backdropFilter: 'blur(5px)',
                    animation: 'fadeIn 0.3s ease-out'
                }}>
                    <div className="glass-card" style={{
                        maxWidth: '500px',
                        width: '90%',
                        padding: '2.5rem',
                        textAlign: 'center',
                        border: '2px solid var(--success)',
                        boxShadow: '0 0 40px rgba(16, 185, 129, 0.3)',
                        animation: 'fadeInUp 0.4s ease-out',
                        background: 'rgba(10, 10, 15, 0.95)'
                    }}>
                        <div style={{
                            width: '80px',
                            height: '80px',
                            borderRadius: '50%',
                            backgroundColor: 'rgba(16, 185, 129, 0.2)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto 1.5rem auto',
                            border: '1px solid var(--success)'
                        }}>
                            <CheckCircle2 size={40} style={{ color: 'var(--success)' }} />
                        </div>

                        <h3 className="text-gradient" style={{
                            fontSize: '1.75rem',
                            marginBottom: '1rem',
                            fontWeight: 'bold'
                        }}>
                            ¡Reserva Exitosa!
                        </h3>

                        <p className="text-muted" style={{
                            fontSize: '1.1rem',
                            marginBottom: '2rem',
                            lineHeight: '1.6',
                            color: 'var(--text-main)'
                        }}>
                            {successMessage || 'Tu configuración ha sido guardada correctamente.'}
                        </p>

                        <button
                            className="btn-primary"
                            style={{
                                width: '100%',
                                padding: '1rem',
                                fontSize: '1.1rem',
                                justifyContent: 'center',
                                fontWeight: 600,
                                background: 'linear-gradient(135deg, var(--success), #059669)',
                                borderColor: 'var(--success)',
                                boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)'
                            }}
                            onClick={async () => {
                                setShowSuccessModal(false);
                                setLoading(true);
                                try {
                                    await loadMyReservation();
                                } catch (e) {
                                    console.error(e);
                                    setError('Error cargando la nueva reserva');
                                } finally {
                                    setLoading(false);
                                }
                            }}
                        >
                            Entendido, ver mi orden
                        </button>
                    </div>
                </div>
            )}
        </div >
    );
};

const ReporterConfig = () => {
    const user = getAuthUser();
    const ok = hasTier(user, 'BRONZE');
    if (!ok) return <SubscriptionGate minTier="BRONZE" title="Reporter (requiere suscripción activa)">{null}</SubscriptionGate>;
    return <ReporterConfigInner />;
};

export default ReporterConfig;