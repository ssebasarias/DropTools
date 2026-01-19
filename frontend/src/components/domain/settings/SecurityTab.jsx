import React from 'react';
import { Smartphone } from 'lucide-react';

const SecurityTab = () => (
    <div className="glass-card fade-in">
        <div style={{ marginBottom: '3rem' }}>
            <h3 style={{ marginBottom: '1.5rem', fontSize: '1.25rem', fontWeight: '600' }}>Security Settings</h3>
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
                        <h4 style={{ fontWeight: '500', marginBottom: '0.25rem' }}>Two-Factor Authentication</h4>
                        <p className="text-muted" style={{ fontSize: '0.9rem' }}>Add an extra layer of security to your account.</p>
                    </div>
                    <button className="btn-primary" style={{ background: 'transparent', border: '1px solid var(--primary)', boxShadow: 'none' }}>Enable</button>
                </div>

                <div style={{ padding: '1.25rem', borderRadius: '12px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--glass-border)' }}>
                    <h4 style={{ fontWeight: '500', marginBottom: '1.5rem' }}>Change Password</h4>
                    <div style={{ display: 'grid', gap: '1rem', maxWidth: '400px' }}>
                        <input type="password" className="glass-input" placeholder="Current Password" />
                        <input type="password" className="glass-input" placeholder="New Password" />
                        <input type="password" className="glass-input" placeholder="Confirm New Password" />
                        <button className="btn-primary" style={{ width: 'fit-content', marginTop: '0.5rem' }}>Update Password</button>
                    </div>
                </div>
            </div>
        </div>

        <div>
            <h3 style={{ marginBottom: '1.5rem', fontSize: '1.25rem', fontWeight: '600', paddingTop: '1rem', borderTop: '1px solid var(--glass-border)' }}>Active Sessions</h3>
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
                            <p className="text-muted" style={{ fontSize: '0.8rem' }}>Bogotá, Colombia • Active now</p>
                        </div>
                    </div>
                    <span className="badge badge-success">Current</span>
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
                            <p className="text-muted" style={{ fontSize: '0.8rem' }}>Bogotá, Colombia • 2 hours ago</p>
                        </div>
                    </div>
                    <button style={{ background: 'transparent', color: 'var(--danger)', fontSize: '0.85rem' }}>Revoke</button>
                </div>
            </div>
        </div>
    </div>
);

export default SecurityTab;
