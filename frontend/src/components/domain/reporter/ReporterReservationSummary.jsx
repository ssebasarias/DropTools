import React from 'react';
import { Mail, CheckCircle2 } from 'lucide-react';

const ReporterReservationSummary = ({ accounts, myReservation, proxyAssigned, hasBronzeAccess }) => {
  if (!myReservation) return null;

  const assignedHour =
    myReservation.slot?.hour_label ?? `${String(myReservation.slot?.hour ?? '').padStart(2, '0')}:00`;
  const defaultEmail = (accounts.find((a) => a.is_default)?.email || accounts[0]?.email) || 'Cuenta vinculada';

  return (
    <div
      className="glass-card"
      style={{
        marginBottom: '2rem',
        border: '2px solid rgba(16,185,129,0.25)',
        animation: 'fadeInUp 0.5s ease-out',
      }}
    >
      <h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Mail size={22} style={{ color: 'var(--primary)' }} />
        Información de cuenta
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <div>
          <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0 0 0.25rem 0' }}>Email Dropi</p>
          <p style={{ margin: 0, fontWeight: 600 }}>{defaultEmail}</p>
        </div>
        <div>
          <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0 0 0.25rem 0' }}>Hora asignada</p>
          <p style={{ margin: 0, fontWeight: 600 }}>{assignedHour}</p>
        </div>
        <div>
          <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0 0 0.25rem 0' }}>Estado de suscripción</p>
          <p style={{ margin: 0, fontWeight: 600 }}>{hasBronzeAccess ? 'Activa' : 'Revisar'}</p>
        </div>
        <div>
          <p className="text-muted" style={{ fontSize: '0.85rem', margin: '0 0 0.25rem 0' }}>Conexión asignada</p>
          <p style={{ margin: 0, fontWeight: 600 }}>{proxyAssigned || 'Sin proxy asignado'}</p>
        </div>
      </div>
      <p
        style={{
          margin: 0,
          marginTop: '1rem',
          fontSize: '1rem',
          color: 'var(--success)',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        <CheckCircle2 size={20} style={{ color: 'var(--success)' }} />
        ¡Todo listo! Tu reporte se ejecutará automáticamente todos los días a las {assignedHour} 🎉
      </p>
    </div>
  );
};

export default ReporterReservationSummary;
