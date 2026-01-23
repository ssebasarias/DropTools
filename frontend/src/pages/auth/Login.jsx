import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Zap, Mail, Lock, ArrowRight, AlertCircle, Eye, EyeOff } from 'lucide-react';

import PublicNavbar from '../../components/layout/PublicNavbar';
import { login as apiLogin } from '../../services/authService';

const Login = () => {
    const navigate = useNavigate();
    const [credentials, setCredentials] = useState({ email: '', password: '' });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const res = await apiLogin(credentials.email, credentials.password);
            const user = res?.user;
            if (user?.is_admin) navigate('/admin', { replace: true });
            else navigate('/user/reporter-setup', { replace: true });
        } catch (err) {
            setError(err.message || 'Error al iniciar sesión');
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <PublicNavbar />
            <div className="auth-container">
                <div className="glass-card auth-card">
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary/20 text-primary mb-4">
                            <Zap size={32} fill="#6366f1" color="#6366f1" />
                        </div>
                        <h2 className="text-2xl font-bold text-main mb-2">Welcome Back</h2>
                        <p className="text-muted">Sign in to access your dashboard</p>
                    </div>

                    {error && (
                        <div style={{
                            padding: '12px 16px',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            borderRadius: '8px',
                            marginBottom: '1.5rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            color: '#ef4444',
                            fontSize: '0.875rem'
                        }}>
                            <AlertCircle size={18} />
                            <span>{error}</span>
                        </div>
                    )}

                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label">Email or Username</label>
                            <div style={{ position: 'relative' }}>
                                <Mail size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                                <input
                                    type="text"
                                    className="glass-input"
                                    style={{ paddingLeft: '38px' }}
                                    placeholder="email or username"
                                    value={credentials.email}
                                    onChange={(e) => setCredentials({ ...credentials, email: e.target.value })}
                                    disabled={loading}
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label className="form-label">Password</label>
                            <div style={{ position: 'relative' }}>
                                <Lock size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', zIndex: 1 }} />
                                <input
                                    type={showPassword ? "text" : "password"}
                                    className="glass-input"
                                    style={{ paddingLeft: '38px', paddingRight: '42px' }}
                                    placeholder="••••••••"
                                    value={credentials.password}
                                    onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                                    disabled={loading}
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    style={{
                                        position: 'absolute',
                                        right: '12px',
                                        top: '50%',
                                        transform: 'translateY(-50%)',
                                        background: 'none',
                                        border: 'none',
                                        cursor: 'pointer',
                                        color: 'var(--text-muted)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        padding: '4px'
                                    }}
                                    tabIndex={-1}
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
                                <input type="checkbox" style={{ accentColor: 'var(--primary)' }} />
                                Remember me
                            </label>
                            <a href="#" style={{ color: 'var(--primary)', textDecoration: 'none' }}>Forgot password?</a>
                        </div>

                        <button
                            type="submit"
                            className="btn-primary"
                            style={{
                                width: '100%',
                                display: 'flex',
                                justifyContent: 'center',
                                alignItems: 'center',
                                gap: '0.5rem',
                                opacity: loading ? 0.7 : 1,
                                cursor: loading ? 'not-allowed' : 'pointer'
                            }}
                            disabled={loading}
                        >
                            {loading ? 'Iniciando...' : 'Sign In'} {!loading && <ArrowRight size={18} />}
                        </button>
                    </form>

                    <div className="text-center mt-6">
                        <p className="text-muted" style={{ fontSize: '0.875rem' }}>
                            Don't have an account? <NavLink to="/register" style={{ color: 'var(--primary)', fontWeight: '500', textDecoration: 'none' }}>Create account</NavLink>
                        </p>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Login;
