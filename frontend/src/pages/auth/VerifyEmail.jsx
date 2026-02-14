import React, { useEffect, useState } from 'react';
import { useSearchParams, NavLink } from 'react-router-dom';

import PublicNavbar from '../../components/layout/PublicNavbar';
import { verifyEmail } from '../../services/authService';
import ErrorAlert from '../../components/common/ErrorAlert';
import SuccessAlert from '../../components/common/SuccessAlert';

const VerifyEmail = () => {
    const [params] = useSearchParams();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    useEffect(() => {
        const token = (params.get('token') || '').trim();
        if (!token) {
            setError('Token inválido.');
            setLoading(false);
            return;
        }

        verifyEmail(token)
            .then((res) => {
                setMessage(res?.detail || 'Email verificado correctamente.');
            })
            .catch((err) => {
                const raw = err.message || 'No se pudo verificar el correo.';
                if (/token invalido|token inválido/i.test(raw)) {
                    setError('Este enlace no es valido o ya expiro. Solicita uno nuevo desde registro.');
                } else {
                    setError(raw);
                }
            })
            .finally(() => setLoading(false));
    }, [params]);

    return (
        <>
            <PublicNavbar />
            <div className="auth-container">
                <div className="glass-card auth-card">
                    <h2 className="text-2xl font-bold text-main mb-4">Verificación de correo</h2>
                    {loading && <p className="text-muted">Validando enlace...</p>}
                    {!loading && (
                        <>
                            <ErrorAlert error={error} onClose={() => setError('')} />
                            <SuccessAlert message={message} onClose={() => setMessage('')} duration={5000} />
                            <div className="text-center mt-4">
                                <NavLink to="/login" style={{ color: 'var(--primary)' }}>
                                    Ir a iniciar sesión
                                </NavLink>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </>
    );
};

export default VerifyEmail;
