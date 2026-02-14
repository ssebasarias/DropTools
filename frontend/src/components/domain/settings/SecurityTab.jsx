import React from 'react';
import { Smartphone } from 'lucide-react';

const SecurityTab = () => (
    <div className="glass-card fade-in">
        <div style={{ marginBottom: '3rem' }}>
            <h3 style={{ marginBottom: '1.5rem', fontSize: '1.25rem', fontWeight: '600' }}>Configuracion de seguridad</h3>
            <div style={{ display: 'grid', gap: '1.5rem' }}>
                <div style={{
                    padding: '1.25rem',
                    borderRadius: '12px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--glass-border)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <div>
                        <h4 style={{ fontWeight: '500', marginBottom: '0.25rem' }}>Autenticacion en dos pasos</h4>
                        <p className="text-muted" style={{ fontSize: '0.9rem' }}>Agrega una capa extra de seguridad a tu cuenta.</p>
                    </div>
                    <button className="btn-primary" style={{ background: 'transparent', border: '1px solid var(--primary)', boxShadow: 'none' }}>Activar</button>
                </div>

                <div style={{ padding: '1.25rem', borderRadius: '12px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--glass-border)' }}>
                    <h4 style={{ fontWeight: '500', marginBottom: '1.5rem' }}>Cambiar contrasena</h4>
                    <div style={{ display: 'grid', gap: '1rem', maxWidth: '400px' }}>
                        <input type="password" className="glass-input" placeholder="Contrasena actual" />
                        <input type="password" className="glass-input" placeholder="Nueva contrasena" />
                        <input type="password" className="glass-input" placeholder="Confirmar nueva contrasena" />
                        <button className="btn-primary" style={{ width: 'fit-content', marginTop: '0.5rem' }}>Actualizar contrasena</button>
                    </div>
                </div>
            </div>
        </div>

        <div>
            <h3 style={{ marginBottom: '1.5rem', fontSize: '1.25rem', fontWeight: '600', paddingTop: '1rem', borderTop: '1px solid var(--glass-border)' }}>Sesiones activas</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '1rem',
                    borderRadius: '10px',
                    background: 'rgba(255,255,255,0.03)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{ padding: '0.5rem', borderRadius: '8px', background: 'rgba(16,185,129,0.15)', color: 'var(--success)' }}>
                            <Smartphone size={20} />
                        </div>
                        <div>
                            <p style={{ fontWeight: '500', marginBottom: '0.2rem' }}>Windows PC • Chrome</p>
                            <p className="text-muted" style={{ fontSize: '0.8rem' }}>Bogota, Colombia • Activa ahora</p>
                        </div>
                    </div>
                    <span className="badge badge-success">Actual</span>
                </div>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '1rem',
                    borderRadius: '10px',
                    background: 'transparent',
                    border: '1px solid var(--glass-border)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{ padding: '0.5rem', borderRadius: '8px', background: 'rgba(148,163,184,0.15)', color: '#94a3b8' }}>
                            <Smartphone size={20} />
                        </div>
                        <div>
                            <p style={{ fontWeight: '500', marginBottom: '0.2rem' }}>iPhone 13 • Safari</p>
                            <p className="text-muted" style={{ fontSize: '0.8rem' }}>Bogota, Colombia • Hace 2 horas</p>
                        </div>
                    </div>
                    <button style={{ background: 'transparent', color: 'var(--danger)', fontSize: '0.85rem' }}>Cerrar sesion</button>
                </div>
            </div>
        </div>
    </div>
);

export default SecurityTab;
