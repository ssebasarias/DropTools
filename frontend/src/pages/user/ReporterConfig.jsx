import React, { useEffect, useState } from 'react';
import { Save, Info, Clock, Mail, Key, Plus, CheckCircle2 } from 'lucide-react';
import { createDropiAccount, fetchDropiAccounts, setDefaultDropiAccount } from '../../services/api';
import SubscriptionGate from '../../components/common/SubscriptionGate';

const ReporterConfig = () => {
    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [creating, setCreating] = useState(false);

    const [form, setForm] = useState({
        label: 'reporter_2',
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
        } catch (e) {
            setError(e.message || 'Error cargando cuentas');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    return (
        <SubscriptionGate minTier="BRONZE" title="Reporter (requiere suscripción activa)">
        <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1>Reporter Configuration</h1>
                <p className="text-muted">Setup your daily report generation automation.</p>
            </div>

            <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem', display: 'flex', gap: '1rem', alignItems: 'start', backgroundColor: 'rgba(99, 102, 241, 0.05)', borderColor: 'rgba(99, 102, 241, 0.2)' }}>
                <Info size={24} className="text-primary" style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                    <h4 style={{ marginBottom: '0.5rem', color: 'var(--primary)' }}>Important Instruction</h4>
                    <p style={{ fontSize: '0.95rem', lineHeight: '1.6', color: 'var(--text-main)' }}>
                        To ensure the security of your main account and proper functionality of the reporter, please
                        <strong> create a secondary account</strong> with restricted permissions if possible.
                        Enter the credentials (email and password) of this secondary account below.
                        The reporter will use these credentials to access your dashboard and generate reports
                        automatically on your behalf.
                    </p>
                </div>
            </div>

            <div className="glass-card">
                <form onSubmit={(e) => e.preventDefault()}>
                    <h3 style={{ marginBottom: '1.5rem' }}>Cuentas secundarias Dropi</h3>

                    {error && (
                        <div style={{ marginBottom: '1rem', color: '#ef4444', fontSize: '0.9rem' }}>
                            {error}
                        </div>
                    )}

                    {loading ? (
                        <p className="text-muted">Cargando cuentas...</p>
                    ) : (
                        <div style={{ display: 'grid', gap: '0.75rem', marginBottom: '1.5rem' }}>
                            {accounts.length === 0 ? (
                                <p className="text-muted">Aún no tienes cuentas secundarias registradas.</p>
                            ) : (
                                accounts.map((a) => (
                                    <div
                                        key={a.id}
                                        className="glass-panel"
                                        style={{
                                            padding: '0.75rem 1rem',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between',
                                            gap: '1rem'
                                        }}
                                    >
                                        <div>
                                            <div style={{ fontWeight: 600 }}>
                                                {a.label} {a.is_default && <span style={{ color: 'var(--primary)' }}>(default)</span>}
                                            </div>
                                            <div className="text-muted" style={{ fontSize: '0.85rem' }}>
                                                {a.email}
                                            </div>
                                        </div>

                                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                                            {!a.is_default && (
                                                <button
                                                    type="button"
                                                    className="btn-secondary"
                                                    onClick={async () => {
                                                        await setDefaultDropiAccount(a.id);
                                                        await load();
                                                    }}
                                                >
                                                    <CheckCircle2 size={16} /> Default
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}

                    <div className="form-group">
                        <label className="form-label">Nueva cuenta Dropi - Email</label>
                        <div style={{ position: 'relative' }}>
                            <Mail size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
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
                        <label className="form-label">Nueva cuenta Dropi - Password</label>
                        <div style={{ position: 'relative' }}>
                            <Key size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                            <input
                                type="password"
                                className="glass-input"
                                style={{ paddingLeft: '38px' }}
                                placeholder="•••••••••"
                                value={form.password}
                                onChange={(e) => setForm({ ...form, password: e.target.value })}
                            />
                        </div>
                    </div>

                    <div style={{ margin: '2rem 0', borderTop: '1px solid var(--glass-border)' }}></div>

                    <h3 style={{ marginBottom: '1.5rem' }}>Schedule Automation</h3>

                    <div className="form-group">
                        <label className="form-label">Daily Execution Time</label>
                        <div style={{ position: 'relative', maxWidth: '200px' }}>
                            <Clock size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                            <input
                                type="time"
                                className="glass-input"
                                style={{ paddingLeft: '38px' }}
                                value={form.executionTime}
                                onChange={(e) => setForm({ ...form, executionTime: e.target.value })}
                            />
                        </div>
                        <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
                            The reporter will run automatically every day at this time.
                        </p>
                    </div>

                    <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'flex-end' }}>
                        <button
                            type="button"
                            className="btn-primary"
                            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: creating ? 0.7 : 1 }}
                            disabled={creating}
                            onClick={async () => {
                                setError('');
                                setCreating(true);
                                try {
                                    await createDropiAccount({
                                        label: form.label || 'reporter_2',
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
                            <Plus size={18} /> Guardar cuenta secundaria
                        </button>
                    </div>
                </form>
            </div>
        </div>
        </SubscriptionGate>
    );
};

export default ReporterConfig;
