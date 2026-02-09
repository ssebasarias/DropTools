import React from 'react';
import { Bot, Mail, Lock, RefreshCw, Shield } from 'lucide-react';

const ReportersTab = () => (
    <div className="glass-card fade-in">
        <div style={{ marginBottom: '2rem' }}>
            <h3 style={{ marginBottom: '0.5rem', fontSize: '1.25rem', fontWeight: '600' }}>Reporter Accounts</h3>
            <p className="text-muted">Manage the secondary accounts used by your worker bots to generate reports.</p>
        </div>

        <div style={{ padding: '1.5rem', borderRadius: '12px', background: 'rgba(99, 102, 241, 0.05)', border: '1px solid rgba(99, 102, 241, 0.2)', marginBottom: '2rem' }}>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                <div style={{ padding: '0.5rem', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.2)', color: 'var(--primary)', flexShrink: 0 }}>
                    <Bot size={24} />
                </div>
                <div style={{ flex: 1 }}>
                    <h4 style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '0.5rem' }}>Active Worker Credentials</h4>
                    <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                        These credentials are used by the automated system to log in as a secondary user and export data.
                        <strong> Do not use your main admin credentials here.</strong>
                    </p>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem' }}>
                        <div className="form-group">
                            <label className="form-label">Worker Email</label>
                            <div style={{ position: 'relative' }}>
                                <Mail size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                                <input type="email" className="glass-input" style={{ paddingLeft: '38px' }} defaultValue="worker.bot@droptools.com" />
                            </div>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Worker Password</label>
                            <div style={{ position: 'relative' }}>
                                <Lock size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                                <input type="password" className="glass-input" style={{ paddingLeft: '38px' }} defaultValue="••••••••••••" />
                            </div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1.5rem' }}>
                        <button style={{ color: 'var(--text-muted)', background: 'transparent', fontSize: '0.9rem', cursor: 'pointer' }}>Test Connection</button>
                        <button className="btn-primary" style={{ padding: '0.5rem 1.5rem' }}>Update Credentials</button>
                    </div>
                </div>
            </div>
        </div>

        <div>
            <h4 style={{ marginBottom: '1rem', fontWeight: '600' }}>History & Logs</h4>
            <div className="glass-panel" style={{ overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                    <thead>
                        <tr style={{ background: 'rgba(255,255,255,0.05)', textAlign: 'left' }}>
                            <th style={{ padding: '1rem' }}>Activity</th>
                            <th style={{ padding: '1rem' }}>Status</th>
                            <th style={{ padding: '1rem' }}>Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style={{ borderBottom: '1px solid var(--glass-border)' }}>
                            <td style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <RefreshCw size={16} className="text-muted" /> Password Rotation
                            </td>
                            <td style={{ padding: '1rem' }}><span className="badge badge-success">Success</span></td>
                            <td style={{ padding: '1rem' }} className="text-muted">2 days ago</td>
                        </tr>
                        <tr>
                            <td style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <Shield size={16} className="text-muted" /> Login Attempt
                            </td>
                            <td style={{ padding: '1rem' }}><span className="badge badge-warning">Verify</span></td>
                            <td style={{ padding: '1rem' }} className="text-muted">5 days ago</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
);

export default ReportersTab;
