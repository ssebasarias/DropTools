import React from 'react';
import { AlertCircle } from 'lucide-react';

const ReporterCancelModal = ({ open, onClose, onConfirm }) => {
  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        animation: 'fadeIn 0.2s ease-out',
      }}
    >
      <div
        className="glass-card"
        style={{
          maxWidth: '500px',
          margin: '1rem',
          animation: 'slideIn 0.3s ease-out',
        }}
      >
        <h3 style={{ marginBottom: '1rem', fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={24} style={{ color: 'var(--warning)' }} />
          ¿Cancelar reserva?
        </h3>
        <p className="text-muted" style={{ marginBottom: '1.5rem', lineHeight: '1.6' }}>
          Si cancelas tu reserva, perderás tu hora asignada y tendrás que configurar todo nuevamente.
          Los reportes automáticos se detendrán hasta que reserves una nueva hora.
        </p>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
          <button type="button" className="btn-secondary" onClick={onClose}>
            No, mantener reserva
          </button>
          <button
            type="button"
            className="btn-primary"
            style={{ background: 'var(--danger)', borderColor: 'var(--danger)' }}
            onClick={onConfirm}
          >
            Si, cancelar reserva
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReporterCancelModal;
