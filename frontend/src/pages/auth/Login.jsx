import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Zap, Mail, Lock, ArrowRight } from 'lucide-react';

import PublicNavbar from '../../components/layout/PublicNavbar';

const Login = () => {
    const navigate = useNavigate();
    const [credentials, setCredentials] = useState({ email: '', password: '' });

    const handleSubmit = (e) => {
        e.preventDefault();
        // Placeholder for future functionality
        console.log('Login attempt:', credentials);
        navigate('/user/dashboard');
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

                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label">Email Address</label>
                            <div style={{ position: 'relative' }}>
                                <Mail size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                                <input
                                    type="email"
                                    className="glass-input"
                                    style={{ paddingLeft: '38px' }}
                                    placeholder="name@company.com"
                                    value={credentials.email}
                                    onChange={(e) => setCredentials({ ...credentials, email: e.target.value })}
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label className="form-label">Password</label>
                            <div style={{ position: 'relative' }}>
                                <Lock size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                                <input
                                    type="password"
                                    className="glass-input"
                                    style={{ paddingLeft: '38px' }}
                                    placeholder="••••••••"
                                    value={credentials.password}
                                    onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                                    required
                                />
                            </div>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
                                <input type="checkbox" style={{ accentColor: 'var(--primary)' }} />
                                Remember me
                            </label>
                            <a href="#" style={{ color: 'var(--primary)', textDecoration: 'none' }}>Forgot password?</a>
                        </div>

                        <button type="submit" className="btn-primary" style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}>
                            Sign In <ArrowRight size={18} />
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
