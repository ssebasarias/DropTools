import React, { useState } from 'react';
import { Save, Info, Clock, Mail, Key } from 'lucide-react';

const ReporterConfig = () => {
    const [config, setConfig] = useState({
        email: '',
        password: '',
        executionTime: '08:00'
    });

    return (
        <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1>Reporter Configuration</h1>
                <p className="text-muted">Setup your daily report generation automation.</p>
            </div>

            <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem', display: 'flex', gap: '1rem', alignItems: 'start', backgroundColor: 'rgba(99, 102, 241, 0.05)', borderColor: 'rgba(99, 102, 241, 0.2)' }}>
                <Info size={24} className="text-primary" style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                    <h4 style={{ marginBottom: '0.5rem', color: 'var(--primary)' }}>Important Instruction</h4>
                    <p style={{ fontSize: '0.95rem', lineHeight: '1.6', color: 'var(--text-main)' }}>
                        To ensure the security of your main account and proper functionality of the reporter, please
                        <strong> create a secondary account</strong> with restricted permissions if possible.
                        Enter the credentials (email and password) of this secondary account below.
                        The reporter will use these credentials to access your dashboard and generate reports
                        automatically on your behalf.
                    </p>
                </div>
            </div>

            <div className="glass-card">
                <form onSubmit={(e) => e.preventDefault()}>
                    <h3 style={{ marginBottom: '1.5rem' }}>Account Credentials</h3>

                    <div className="form-group">
                        <label className="form-label">Secondary Account Email</label>
                        <div style={{ position: 'relative' }}>
                            <Mail size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                            <input
                                type="email"
                                className="glass-input"
                                style={{ paddingLeft: '38px' }}
                                placeholder="reporter@yourdomain.com"
                                value={config.email}
                                onChange={(e) => setConfig({ ...config, email: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Secondary Account Password</label>
                        <div style={{ position: 'relative' }}>
                            <Key size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                            <input
                                type="password"
                                className="glass-input"
                                style={{ paddingLeft: '38px' }}
                                placeholder="•••••••••"
                                value={config.password}
                                onChange={(e) => setConfig({ ...config, password: e.target.value })}
                            />
                        </div>
                    </div>

                    <div style={{ margin: '2rem 0', borderTop: '1px solid var(--glass-border)' }}></div>

                    <h3 style={{ marginBottom: '1.5rem' }}>Schedule Automation</h3>

                    <div className="form-group">
                        <label className="form-label">Daily Execution Time</label>
                        <div style={{ position: 'relative', maxWidth: '200px' }}>
                            <Clock size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                            <input
                                type="time"
                                className="glass-input"
                                style={{ paddingLeft: '38px' }}
                                value={config.executionTime}
                                onChange={(e) => setConfig({ ...config, executionTime: e.target.value })}
                            />
                        </div>
                        <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
                            The reporter will run automatically every day at this time.
                        </p>
                    </div>

                    <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'flex-end' }}>
                        <button className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Save size={18} /> Save Configuration
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ReporterConfig;
