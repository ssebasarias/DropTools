import React from 'react';
import { Bot, RefreshCw, Bell } from 'lucide-react';

const NotificationsTab = () => (
    <div className="glass-card fade-in">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
            <div>
                <h3 style={{ marginBottom: '0.5rem', fontSize: '1.25rem', fontWeight: '600' }}>Notifications</h3>
                <p className="text-muted">Stay updated with system activities and alerts.</p>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="badge" style={{ background: 'var(--primary)', color: 'white', border: 'none', padding: '0.5rem 1rem', cursor: 'pointer' }}>All</button>
                <button className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', border: '1px solid var(--glass-border)', padding: '0.5rem 1rem', cursor: 'pointer' }}>Unread</button>
                <button className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', border: '1px solid var(--glass-border)', padding: '0.5rem 1rem', cursor: 'pointer' }}>Archived</button>
            </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Notification Item 1 - Success */}
            <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', gap: '1rem', alignItems: 'flex-start', borderLeft: '4px solid var(--success)' }}>
                <div style={{ padding: '0.5rem', borderRadius: '50%', background: 'rgba(16,185,129,0.15)', color: 'var(--success)' }}>
                    <Bot size={20} />
                </div>
                <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <h4 style={{ fontSize: '1rem', fontWeight: '600' }}>Reporter Task Completed</h4>
                        <span className="text-muted" style={{ fontSize: '0.8rem' }}>2 min ago</span>
                    </div>
                    <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>The daily sales report for <strong>Oct 24</strong> has been successfully generated and archived.</p>
                    <button style={{ fontSize: '0.85rem', color: 'var(--primary)', background: 'transparent', fontWeight: '500', border: 'none', cursor: 'pointer', padding: 0 }}>View Report</button>
                </div>
            </div>

            {/* Notification Item 2 - Warning */}
            <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', gap: '1rem', alignItems: 'flex-start', borderLeft: '4px solid var(--warning)' }}>
                <div style={{ padding: '0.5rem', borderRadius: '50%', background: 'rgba(245,158,11,0.15)', color: 'var(--warning)' }}>
                    <RefreshCw size={20} />
                </div>
                <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <h4 style={{ fontSize: '1rem', fontWeight: '600' }}>Rate Limit Approaching</h4>
                        <span className="text-muted" style={{ fontSize: '0.8rem' }}>1 hr ago</span>
                    </div>
                    <p className="text-muted" style={{ fontSize: '0.9rem' }}>The worker bot is approaching the daily request limit (85% used). Consider pausing non-essential tasks.</p>
                </div>
            </div>

            {/* Notification Item 3 - Info */}
            <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', gap: '1rem', alignItems: 'flex-start', opacity: 0.7 }}>
                <div style={{ padding: '0.5rem', borderRadius: '50%', background: 'rgba(99,102,241,0.15)', color: 'var(--primary)' }}>
                    <Bell size={20} />
                </div>
                <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <h4 style={{ fontSize: '1rem', fontWeight: '600' }}>System Update</h4>
                        <span className="text-muted" style={{ fontSize: '0.8rem' }}>Yesterday</span>
                    </div>
                    <p className="text-muted" style={{ fontSize: '0.9rem' }}>DropTools platform was updated to v2.1.0 with new security features.</p>
                </div>
            </div>
        </div>

        <div style={{ textAlign: 'center', marginTop: '2rem' }}>
            <button style={{ background: 'transparent', color: 'var(--text-muted)', fontSize: '0.9rem', border: 'none', cursor: 'pointer' }}>Load older notifications</button>
        </div>
    </div>
);

export default NotificationsTab;
