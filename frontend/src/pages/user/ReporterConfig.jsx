import React, { useEffect, useState, useCallback } from 'react';
import { Save, Info, Clock, Mail, Key, Plus, CheckCircle2, XCircle, RefreshCw, FileText, Phone, User, Package, Square, Calendar, BarChart3 } from 'lucide-react';
import { createDropiAccount, fetchDropiAccounts, setDefaultDropiAccount, fetchReporterConfig, updateReporterConfig, stopReporterProcesses, fetchReporterStatus, fetchReporterList, fetchReporterEnv, fetchReporterSlots, fetchMyReservation, createReservation, deleteReservation, fetchReporterRuns, fetchReporterRunProgress } from '../../services/api';
import SubscriptionGate from '../../components/common/SubscriptionGate';
import { getAuthUser } from '../../services/authService';
import { hasTier } from '../../utils/subscription';
import ErrorState from '../../components/common/ErrorState';
import EmptyState from '../../components/common/EmptyState';

const ReporterConfigInner = () => {
    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [creating, setCreating] = useState(false);

    // Reporter status & control
    const [starting, setStarting] = useState(false);
    const [stoppingProcesses, setStoppingProcesses] = useState(false);
    const [status, setStatus] = useState(null);
    const [statusLoading, setStatusLoading] = useState(false);
    const [reportsList, setReportsList] = useState([]);
    const [reportsLoading, setReportsLoading] = useState(false);
    const [workflowProgress, setWorkflowProgress] = useState(null);
    const [reporterEnv, setReporterEnv] = useState(null); // { dahell_env, reporter_use_celery, message }

    // Slots & reservations (nuevo sistema por hora)
    const [slots, setSlots] = useState([]);
    const [slotsLoading, setSlotsLoading] = useState(false);
    const [myReservation, setMyReservation] = useState(null);
    const [reservationSaving, setReservationSaving] = useState(false);
    const [runs, setRuns] = useState([]);
    const [lastRunProgress, setLastRunProgress] = useState(null);
    const [selectedSlotId, setSelectedSlotId] = useState(null);
    const [monthlyOrdersEstimate, setMonthlyOrdersEstimate] = useState(0);

    const [form, setForm] = useState({
        label: 'reporter',
        email: '',
        password: '',
        is_default: false,
        executionTime: '08:00'
    });

    const load = useCallback(async () => {
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
        setReservationSaving(true);
        try {
            await createReservation({ slot_id: selectedSlotId, monthly_orders_estimate: monthlyOrdersEstimate });
            await loadMyReservation();
            await loadSlots();
        } catch (e) {
            setError(e.message || 'No se pudo crear la reserva');
        } finally {
            setReservationSaving(false);
        }
    };

    const handleCancelReservation = async () => {
        setError('');
        try {
            await deleteReservation();
            setMyReservation(null);
            setSelectedSlotId(null);
            await loadSlots();
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
            setReporterEnv({ dahell_env: 'production', reporter_use_celery: true });
        }
    }, []);

    const loadSlots = useCallback(async () => {
        setSlotsLoading(true);
        try {
            const data = await fetchReporterSlots();
            setSlots(data);
        } catch (e) {
            console.error('Error loading slots:', e);
        } finally {
            setSlotsLoading(false);
        }
    }, []);

    const loadMyReservation = useCallback(async () => {
        try {
            const data = await fetchMyReservation();
            setMyReservation(data);
            if (data?.slot_id) setSelectedSlotId(data.slot_id);
            if (data?.slot?.id) setSelectedSlotId(data.slot.id);
            if (data?.monthly_orders_estimate != null) setMonthlyOrdersEstimate(data.monthly_orders_estimate);
        } catch (e) {
            setMyReservation(null);
        }
    }, []);

    const loadRunsAndProgress = useCallback(async () => {
        try {
            const runsData = await fetchReporterRuns(7);
            setRuns(runsData || []);
            const firstRun = (runsData || [])[0];
            if (firstRun?.id) {
                const progress = await fetchReporterRunProgress(firstRun.id);
                setLastRunProgress(progress);
            } else {
                setLastRunProgress(null);
            }
        } catch (e) {
            setRuns([]);
            setLastRunProgress(null);
        }
    }, []);

    useEffect(() => {
        load();
        loadStatus();
        loadReportsList();
        loadReporterEnv();
        loadSlots();
        loadMyReservation();
        loadRunsAndProgress();
    }, [load, loadStatus, loadReportsList, loadReporterEnv, loadSlots, loadMyReservation, loadRunsAndProgress]);

    // Auto-refresh status cuando el workflow está corriendo (contador y panel se actualizan al marcar órdenes)
    useEffect(() => {
        const isWorkflowRunning = workflowProgress &&
            ['step1_running', 'step2_running', 'step3_running', 'step1_completed', 'step2_completed'].includes(workflowProgress.status);
        const isStep3 = workflowProgress?.status === 'step3_running';

        let interval;
        const ms = isStep3 ? 2000 : (isWorkflowRunning ? 3000 : 10000);

        interval = setInterval(() => {
            loadStatus(true);
            if (isWorkflowRunning) loadReportsList(true);
        }, ms);

        return () => clearInterval(interval);
    }, [workflowProgress?.status, loadStatus, loadReportsList]);

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
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                    <h1 className="text-gradient" style={{ fontSize: '2.5rem', margin: 0 }}>Reporter Configuration</h1>
                    {reporterEnv && (
                        <span
                            title={reporterEnv.message || (reporterEnv.run_mode === 'development_docker' ? 'Reporter vía Celery en Docker (pruebas)' : reporterEnv.dahell_env === 'development' ? 'Reporter en proceso (navegador visible)' : 'Reporter vía Celery (producción)')}
                            style={{
                                padding: '0.35rem 0.75rem',
                                borderRadius: '9999px',
                                fontSize: '0.8rem',
                                fontWeight: 600,
                                backgroundColor: reporterEnv.run_mode === 'development_docker' ? 'rgba(245, 158, 11, 0.2)' : reporterEnv.dahell_env === 'development' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(99, 102, 241, 0.2)',
                                color: reporterEnv.run_mode === 'development_docker' ? 'var(--warning)' : reporterEnv.dahell_env === 'development' ? 'var(--success)' : 'var(--primary)',
                                border: `1px solid ${reporterEnv.run_mode === 'development_docker' ? 'var(--warning)' : reporterEnv.dahell_env === 'development' ? 'var(--success)' : 'var(--primary)'}`,
                            }}
                        >
                            {reporterEnv.run_mode === 'development_docker' ? 'Modo desarrollo (Docker)' : reporterEnv.dahell_env === 'development' ? 'Modo desarrollo' : 'Modo producción'}
                        </span>
                    )}
                </div>
                <p className="text-muted" style={{ marginTop: '0.5rem' }}>Gestiona la generación de reportes de órdenes sin movimiento.</p>
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

                    {error && (
                        <div style={{
                            marginBottom: '1rem',
                            padding: '0.75rem 1rem',
                            background: 'rgba(239,68,68,0.1)',
                            border: '1px solid rgba(239,68,68,0.3)',
                            borderRadius: '8px',
                            color: '#ef4444',
                            fontSize: '0.9rem',
                            whiteSpace: 'pre-wrap',
                            maxHeight: '200px',
                            overflow: 'auto'
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
                        <label className="form-label">Correo Electrónico</label>
                        <div style={{ position: 'relative' }}>
                            <Mail size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', zIndex: 1 }} />
                            <input
                                type="email"
                                className="glass-input"
                                style={{ paddingLeft: '38px', opacity: accounts.length > 0 ? 0.6 : 1 }}
                                placeholder="reporter@yourdomain.com"
                                value={form.email}
                                onChange={(e) => setForm({ ...form, email: e.target.value })}
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

            {/* Slots y reserva por hora (nuevo sistema) */}
            <div className="glass-card" style={{ marginBottom: '2rem' }}>
                <h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Calendar size={22} style={{ color: 'var(--primary)' }} />
                    Reserva por hora diaria
                </h3>
                <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                    Elige la hora en que se ejecutará tu reporter cada día. Si una hora está llena, no se aceptan más usuarios.
                </p>
                {slotsLoading ? (
                    <p className="text-muted">Cargando horarios...</p>
                ) : (
                    <>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(80px, 1fr))', gap: '0.5rem', marginBottom: '1.5rem' }}>
                            {slots.map((s) => (
                                <button
                                    key={s.id}
                                    type="button"
                                    onClick={() => !s.available ? null : setSelectedSlotId(s.id)}
                                    disabled={!s.available}
                                    style={{
                                        padding: '0.6rem',
                                        borderRadius: '10px',
                                        border: selectedSlotId === s.id ? '2px solid var(--primary)' : '1px solid var(--glass-border)',
                                        background: selectedSlotId === s.id ? 'rgba(99,102,241,0.2)' : (s.available ? 'var(--glass-bg)' : 'rgba(239,68,68,0.1)'),
                                        color: s.available ? 'var(--text-main)' : 'var(--text-muted)',
                                        cursor: s.available ? 'pointer' : 'not-allowed',
                                        fontSize: '0.85rem',
                                        fontWeight: 600
                                    }}
                                    title={s.available ? `${s.hour_label} - ${s.current_users}/${s.max_users} usuarios` : `Lleno (${s.max_users} usuarios)`}
                                >
                                    {s.hour_label}
                                    <div style={{ fontSize: '0.7rem', fontWeight: 400, marginTop: '0.2rem', color: 'var(--text-muted)' }}>
                                        {s.current_users}/{s.max_users}
                                    </div>
                                </button>
                            ))}
                        </div>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: '1rem' }}>
                            <div style={{ flex: '1 1 200px' }}>
                                <label className="form-label" style={{ display: 'block', marginBottom: '0.35rem' }}>Órdenes mensuales aproximadas</label>
                                <input
                                    type="number"
                                    min={0}
                                    className="glass-input"
                                    value={monthlyOrdersEstimate || ''}
                                    onChange={(e) => setMonthlyOrdersEstimate(parseInt(e.target.value, 10) || 0)}
                                    placeholder="Ej. 500"
                                    style={{ width: '100%', maxWidth: '180px' }}
                                />
                            </div>
                            <button
                                type="button"
                                className="btn-primary"
                                disabled={!selectedSlotId || reservationSaving}
                                onClick={handleConfirmReservation}
                                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                            >
                                {reservationSaving ? <RefreshCw size={18} className="spinning" /> : <CheckCircle2 size={18} />}
                                {reservationSaving ? 'Guardando...' : 'Confirmar reserva'}
                            </button>
                        </div>
                        {myReservation && (
                            <div style={{
                                padding: '1rem',
                                background: 'rgba(16,185,129,0.08)',
                                border: '1px solid rgba(16,185,129,0.25)',
                                borderRadius: '12px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                flexWrap: 'wrap',
                                gap: '1rem'
                            }}>
                                <div>
                                    <strong style={{ color: 'var(--success)' }}>Tu reserva:</strong>{' '}
                                    {myReservation.slot?.hour_label ?? `${String(myReservation.slot?.hour ?? '').padStart(2, '0')}:00`} ·{' '}
                                    ~{myReservation.estimated_pending_orders ?? 0} órdenes pendientes estimadas
                                </div>
                                <button type="button" className="btn-secondary" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }} onClick={handleCancelReservation}>
                                    Cancelar reserva
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>

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
                            {lastRunProgress.users.map((u, idx) => (
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

            {/* KPI Contador de Reportes del Día */}
            <div className="glass-card" style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '2rem', flexWrap: 'wrap' }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '1rem',
                        padding: '1rem 1.5rem',
                        background: 'rgba(99,102,241,0.1)',
                        borderRadius: '12px',
                        border: '1px solid rgba(99,102,241,0.2)'
                    }}>
                        <div style={{ padding: '0.75rem', background: 'rgba(99,102,241,0.2)', borderRadius: '10px' }}>
                            <FileText size={24} style={{ color: 'var(--primary)' }} />
                        </div>
                        <div>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0, marginBottom: '0.25rem' }}>Reportes realizados hoy</p>
                            <h2 style={{ fontSize: '2.5rem', margin: 0, fontWeight: 'bold', background: 'linear-gradient(135deg, var(--primary), #4f46e5)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                {status?.total_reported || 0}
                            </h2>
                        </div>
                    </div>
                    <button type="button" className="btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }} onClick={() => { loadSlots(); loadMyReservation(); loadRunsAndProgress(); loadStatus(); loadReportsList(); }}>
                        <RefreshCw size={16} />
                        Actualizar
                    </button>
                </div>
            </div>

            {/* Panel de Progreso del Workflow */}
            {workflowProgress && (
                <div className="glass-card" style={{ marginBottom: '2rem', border: '2px solid rgba(99,102,241,0.3)' }}>
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
                    <EmptyState
                        icon={Package}
                        title="No hay órdenes reportadas aún"
                        description="Los reportes se ejecutan automáticamente según tu reserva por hora."
                    />
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
    if (!ok) return <SubscriptionGate minTier="BRONZE" title="Reporter (requiere suscripción activa)">{null}</SubscriptionGate>;
    return <ReporterConfigInner />;
};

export default ReporterConfig;