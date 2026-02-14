import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Zap, Mail, Lock, User, ArrowRight } from 'lucide-react';
import { GoogleLogin } from '@react-oauth/google';

import PublicNavbar from '../../components/layout/PublicNavbar';
import { register as apiRegister, loginWithGoogle } from '../../services/authService';
import { getUserHomePath } from '../../utils/subscription';
import ErrorAlert from '../../components/common/ErrorAlert';
import SuccessAlert from '../../components/common/SuccessAlert';

const Register = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        confirmPassword: ''
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [googleLoading, setGoogleLoading] = useState(false);
    const [passwordStrength, setPasswordStrength] = useState({ strength: 0, label: '', color: '' });

    // Función para calcular fuerza de contraseña
    const getPasswordStrength = (password) => {
        if (!password) return { strength: 0, label: '', color: '' };
        
        let strength = 0;
        
        // Longitud
        if (password.length >= 8) strength += 25;
        if (password.length >= 12) strength += 25;
        
        // Mayúsculas
        if (/[A-Z]/.test(password)) strength += 15;
        
        // Minúsculas
        if (/[a-z]/.test(password)) strength += 15;
        
        // Números
        if (/[0-9]/.test(password)) strength += 10;
        
        // Caracteres especiales
        if (/[^A-Za-z0-9]/.test(password)) strength += 10;
        
        let label = '';
        let color = '';
        
        if (strength < 30) {
            label = 'Muy débil';
            color = '#ef4444';
        } else if (strength < 50) {
            label = 'Débil';
            color = '#f59e0b';
        } else if (strength < 75) {
            label = 'Buena';
            color = '#3b82f6';
        } else {
            label = 'Fuerte';
            color = '#10b981';
        }
        
        return { strength, label, color };
    };

    // Handler para login con Google
    const handleGoogleSuccess = async (credentialResponse) => {
        setError('');
        setGoogleLoading(true);
        
        try {
            // El token viene en credentialResponse.credential
            const result = await loginWithGoogle(credentialResponse.credential);
            
            // Redirigir según el rol
            const user = result?.user;
            if (user?.is_admin) {
                navigate('/admin', { replace: true });
            } else {
                navigate(getUserHomePath(user), { replace: true });
            }
        } catch (err) {
            setError(err.message || 'Error al registrarse con Google');
        } finally {
            setGoogleLoading(false);
        }
    };

    const handleGoogleError = () => {
        setError('Error al conectar con Google');
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        if (formData.password !== formData.confirmPassword) {
            setError('Las contraseñas no coinciden');
            return;
        }
        setLoading(true);
        apiRegister({
            name: formData.name,
            email: formData.email,
            password: formData.password
        }).then((res) => {
            setSuccess(res?.detail || 'Te enviamos un correo de verificación. Revisa tu bandeja.');
            setFormData({ name: '', email: '', password: '', confirmPassword: '' });
            setPasswordStrength({ strength: 0, label: '', color: '' });
            setTimeout(() => navigate('/login', { replace: true }), 2200);
        }).catch((err) => {
            setError(err.message || 'Error al registrarse');
        }).finally(() => setLoading(false));
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
                        <h2 className="text-2xl font-bold text-main mb-2">Crear cuenta</h2>
                        <p className="text-muted">Empieza a usar DropTools hoy</p>
                    </div>

                    <ErrorAlert error={error} onClose={() => setError('')} />
                    <SuccessAlert message={success} onClose={() => setSuccess('')} duration={2500} />

                    {/* Botón de Google OAuth */}
                    <div style={{ marginBottom: '1.5rem' }}>
                        <GoogleLogin
                            onSuccess={handleGoogleSuccess}
                            onError={handleGoogleError}
                            useOneTap={false}
                            theme="outline"
                            size="large"
                            text="signup_with"
                            shape="rectangular"
                            width="100%"
                            disabled={loading || googleLoading}
                        />
                    </div>

                    {/* Separador "o" */}
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '1rem',
                        marginBottom: '1.5rem'
                    }}>
                        <div style={{ flex: 1, height: '1px', background: 'var(--glass-border)' }}></div>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>o</span>
                        <div style={{ flex: 1, height: '1px', background: 'var(--glass-border)' }}></div>
                    </div>

                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label">Nombre completo</label>
                            <div style={{ position: 'relative' }}>
                                <User size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                                <input
                                    type="text"
                                    className="glass-input"
                                    style={{ paddingLeft: '38px' }}
                                    placeholder="Ej. Maria Garcia"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    disabled={loading}
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label className="form-label">Correo electronico</label>
                            <div style={{ position: 'relative' }}>
                                <Mail size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                                <input
                                    type="email"
                                    className="glass-input"
                                    style={{ paddingLeft: '38px' }}
                                    placeholder="tu@correo.com"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    disabled={loading || googleLoading}
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label className="form-label">Contrasena</label>
                            <div style={{ position: 'relative' }}>
                                <Lock size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                                <input
                                    type="password"
                                    className="glass-input"
                                    style={{ paddingLeft: '38px' }}
                                    placeholder="Crea una contrasena"
                                    value={formData.password}
                                    onChange={(e) => {
                                        setFormData({ ...formData, password: e.target.value });
                                        setPasswordStrength(getPasswordStrength(e.target.value));
                                    }}
                                    disabled={loading}
                                    required
                                />
                            </div>
                            {/* Indicador de fuerza */}
                            {formData.password && (
                                <div style={{ marginTop: '0.5rem' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Fuerza de contraseña:</span>
                                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: passwordStrength.color }}>
                                            {passwordStrength.label}
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
                                            width: `${passwordStrength.strength}%`,
                                            background: passwordStrength.color,
                                            transition: 'width 0.3s ease, background 0.3s ease',
                                            borderRadius: '2px'
                                        }}></div>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="form-group">
                            <label className="form-label">Confirmar contrasena</label>
                            <div style={{ position: 'relative' }}>
                                <Lock size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                                <input
                                    type="password"
                                    className="glass-input"
                                    style={{ paddingLeft: '38px' }}
                                    placeholder="Repite tu contrasena"
                                    value={formData.confirmPassword}
                                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                                    disabled={loading || googleLoading}
                                    required
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="btn-primary"
                            style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', opacity: (loading || googleLoading) ? 0.7 : 1 }}
                            disabled={loading || googleLoading}
                        >
                            {loading ? 'Creando cuenta...' : 'Crear cuenta'} {!loading && <ArrowRight size={18} />}
                        </button>
                    </form>

                    <div className="text-center mt-6">
                        <p className="text-muted" style={{ fontSize: '0.875rem' }}>
                            ¿Ya tienes cuenta? <NavLink to="/login" style={{ color: 'var(--primary)', fontWeight: '500', textDecoration: 'none' }}>Iniciar sesion</NavLink>
                        </p>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Register;
