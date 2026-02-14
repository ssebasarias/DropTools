import React, { useEffect } from 'react';
import { CheckCircle2 } from 'lucide-react';

const SuccessAlert = ({ message, onClose, duration = 3000 }) => {
    useEffect(() => {
        if (message && onClose) {
            const timer = setTimeout(() => {
                onClose();
            }, duration);
            return () => clearTimeout(timer);
        }
    }, [message, onClose, duration]);
    
    if (!message) return null;
    
    return (
        <div
            role="status"
            aria-live="polite"
            style={{
            padding: '12px 16px',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            animation: 'slideIn 0.3s ease-out'
        }}>
            <CheckCircle2 size={20} style={{ color: 'var(--success)', flexShrink: 0 }} />
            <p style={{ 
                margin: 0, 
                color: 'var(--success)', 
                fontSize: '0.875rem',
                fontWeight: 500
            }}>
                {message}
            </p>
        </div>
    );
};

export default SuccessAlert;
