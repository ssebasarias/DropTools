import React from 'react';
import { NavLink } from 'react-router-dom';

const NotFound = () => {
  return (
    <div style={{ minHeight: '70vh', display: 'grid', placeItems: 'center', padding: '2rem' }}>
      <div className="glass-card" style={{ maxWidth: '560px', textAlign: 'center' }}>
        <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>404</h1>
        <h2 style={{ marginBottom: '1rem' }}>Pagina no encontrada</h2>
        <p className="text-muted" style={{ marginBottom: '1.5rem' }}>
          La ruta que intentaste abrir no existe o fue movida.
        </p>
        <NavLink to="/" className="btn-primary" style={{ textDecoration: 'none' }}>
          Ir al inicio
        </NavLink>
      </div>
    </div>
  );
};

export default NotFound;
