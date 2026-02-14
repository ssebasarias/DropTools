import React from 'react';
import { CheckCircle2 } from 'lucide-react';

const ReporterSuccessModal = ({ open, message, onAcknowledge }) => {
  if (!open) return null;

  return (
    <div
      style={{
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
        animation: 'fadeIn 0.3s ease-out',
      }}
    >
      <div
        className="glass-card"
        style={{
          maxWidth: '500px',
          width: '90%',
          padding: '2.5rem',
          textAlign: 'center',
          border: '2px solid var(--success)',
          boxShadow: '0 0 40px rgba(16, 185, 129, 0.3)',
          animation: 'fadeInUp 0.4s ease-out',
          background: 'rgba(10, 10, 15, 0.95)',
        }}
      >
        <div
          style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            backgroundColor: 'rgba(16, 185, 129, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.5rem auto',
            border: '1px solid var(--success)',
          }}
        >
          <CheckCircle2 size={40} style={{ color: 'var(--success)' }} />
        </div>

        <h3 className="text-gradient" style={{ fontSize: '1.75rem', marginBottom: '1rem', fontWeight: 'bold' }}>
          ¡Reserva exitosa!
        </h3>

        <p
          className="text-muted"
          style={{ fontSize: '1.1rem', marginBottom: '2rem', lineHeight: '1.6', color: 'var(--text-main)' }}
        >
          {message || 'Tu configuración quedó guardada correctamente.'}
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
            boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)',
          }}
          onClick={onAcknowledge}
        >
          Entendido
        </button>
      </div>
    </div>
  );
};

export default ReporterSuccessModal;
