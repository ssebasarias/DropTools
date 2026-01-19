import React from 'react';
import { Save } from 'lucide-react';

const ProfileTab = () => (
    <div className="glass-card fade-in">
        <h3 style={{ marginBottom: '1.5rem', fontSize: '1.25rem', fontWeight: '600' }}>Profile Information</h3>
        <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', cursor: 'pointer' }}>
                <div style={{
                    width: '100px',
                    height: '100px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, var(--primary), #4f46e5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '2rem',
                    fontWeight: 'bold',
                    border: '4px solid rgba(255,255,255,0.05)'
                }}>
                    AD
                </div>
            </div>
            <div style={{ flex: 1, minWidth: '300px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
                    <div className="form-group">
                        <label className="form-label">Full Name</label>
                        <input type="text" className="glass-input" defaultValue="Admin User" />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Username</label>
                        <input type="text" className="glass-input" defaultValue="@admin_dahell" />
                    </div>
                    <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                        <label className="form-label">Email Address</label>
                        <input type="email" className="glass-input" defaultValue="admin@dahell.intelligence.com" />
                    </div>
                    <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                        <label className="form-label">Bio</label>
                        <textarea className="glass-input" style={{ height: '100px', resize: 'none' }} defaultValue="Superuser account for system administration and monitoring." />
                    </div>
                </div>
            </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--glass-border)' }}>
            <button className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Save size={18} /> Save Changes
            </button>
        </div>
    </div>
);

export default ProfileTab;
