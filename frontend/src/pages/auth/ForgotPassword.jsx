import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';

import PublicNavbar from '../../components/layout/PublicNavbar';
import { passwordResetRequest } from '../../services/authService';
import ErrorAlert from '../../components/common/ErrorAlert';
import SuccessAlert from '../../components/common/SuccessAlert';

const ForgotPassword = () => {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');
        setLoading(true);
        try {
            const res = await passwordResetRequest(email);
            setMessage(res?.detail || 'Si el email existe, enviaremos instrucciones.');
        } catch (err) {
            setError(err.message || 'No se pudo procesar la solicitud.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <PublicNavbar />
            <div className="auth-container">
                <div className="glass-card auth-card">
                    <h2 className="text-2xl font-bold text-main mb-4">Olvidé mi contraseña</h2>
                    <p className="text-muted mb-6">Ingresa tu email y te enviaremos un enlace para restablecerla.</p>
                    <ErrorAlert error={error} onClose={() => setError('')} />
                    <SuccessAlert message={message} onClose={() => setMessage('')} duration={5000} />
                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label">Email</label>
                            <input
                                type="email"
                                className="glass-input"
                                placeholder="name@company.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                disabled={loading}
                                required
                            />
                        </div>
                        <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={loading}>
                            {loading ? 'Enviando...' : 'Enviar enlace'}
                        </button>
                    </form>
                    <div className="text-center mt-6">
                        <NavLink to="/login" style={{ color: 'var(--primary)' }}>
                            Volver al login
                        </NavLink>
                    </div>
                </div>
            </div>
        </>
    );
};

export default ForgotPassword;
