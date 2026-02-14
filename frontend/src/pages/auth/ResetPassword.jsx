import React, { useState } from 'react';
import { useSearchParams, NavLink } from 'react-router-dom';

import PublicNavbar from '../../components/layout/PublicNavbar';
import { passwordResetConfirm } from '../../services/authService';
import ErrorAlert from '../../components/common/ErrorAlert';
import SuccessAlert from '../../components/common/SuccessAlert';

const ResetPassword = () => {
    const [params] = useSearchParams();
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    const token = (params.get('token') || '').trim();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');

        if (!token) {
            setError('Token inválido.');
            return;
        }
        if (newPassword !== confirmPassword) {
            setError('Las contraseñas no coinciden.');
            return;
        }

        setLoading(true);
        try {
            const res = await passwordResetConfirm(token, newPassword);
            setMessage(res?.detail || 'Contraseña actualizada correctamente.');
            setNewPassword('');
            setConfirmPassword('');
        } catch (err) {
            const raw = err.message || 'No se pudo actualizar la contraseña.';
            if (/token invalido|token inválido/i.test(raw)) {
                setError('El enlace no es valido o ya expiro. Solicita uno nuevo.');
            } else {
                setError(raw);
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <PublicNavbar />
            <div className="auth-container">
                <div className="glass-card auth-card">
                    <h2 className="text-2xl font-bold text-main mb-4">Restablecer contraseña</h2>
                    <ErrorAlert error={error} onClose={() => setError('')} />
                    <SuccessAlert message={message} onClose={() => setMessage('')} duration={5000} />
                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label">Nueva contraseña</label>
                            <input
                                type="password"
                                className="glass-input"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                disabled={loading}
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Confirmar contraseña</label>
                            <input
                                type="password"
                                className="glass-input"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                disabled={loading}
                                required
                            />
                        </div>
                        <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={loading}>
                            {loading ? 'Actualizando...' : 'Actualizar contraseña'}
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

export default ResetPassword;
