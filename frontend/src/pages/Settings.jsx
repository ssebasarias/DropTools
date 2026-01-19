import React, { useState } from 'react';
import { User, Shield, Bot, Eye, Bell, CreditCard, LogOut } from 'lucide-react';
import Subscriptions from './Subscriptions';

import ProfileTab from '../components/domain/settings/ProfileTab';
import SecurityTab from '../components/domain/settings/SecurityTab';
import ReportersTab from '../components/domain/settings/ReportersTab';
import PreferencesTab from '../components/domain/settings/PreferencesTab';
import NotificationsTab from '../components/domain/settings/NotificationsTab';

const Settings = ({ type = 'admin' }) => {
    const [activeTab, setActiveTab] = useState('profile');

    const tabs = [
        { id: 'profile', label: 'Profile', icon: User },
        { id: 'security', label: 'Security', icon: Shield },
        { id: 'reporters', label: 'Worker Accounts', icon: Bot },
        { id: 'preferences', label: 'Preferences', icon: Eye },
        { id: 'notifications', label: 'Notifications', icon: Bell },
    ];

    if (type === 'user') {
        tabs.splice(2, 0, { id: 'billing', label: 'Plan & Billing', icon: CreditCard });
    }

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Settings</h1>
                <p className="text-muted">Manage your account settings and preferences.</p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }} className="settings-layout">
                {/* Simplified responsive layout using flex */}
                <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>

                    {/* Sidebar Tabs */}
                    <div className="glass-panel" style={{
                        flexShrink: 0,
                        width: '260px',
                        padding: '0.5rem',
                        height: 'fit-content',
                        alignSelf: 'start'
                    }}>
                        {tabs.map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.75rem',
                                    width: '100%',
                                    padding: '0.85rem 1rem',
                                    borderRadius: '10px',
                                    background: activeTab === tab.id ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                                    color: activeTab === tab.id ? 'var(--primary)' : 'var(--text-muted)',
                                    border: 'none',
                                    cursor: 'pointer',
                                    textAlign: 'left',
                                    fontSize: '0.95rem',
                                    fontWeight: '500',
                                    transition: 'all 0.2s',
                                    marginBottom: '0.25rem'
                                }}
                            >
                                <tab.icon size={18} />
                                {tab.label}
                            </button>
                        ))}

                        <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--glass-border)' }}>
                            <button
                                onClick={() => window.location.href = '/login'}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.75rem',
                                    width: '100%',
                                    padding: '0.85rem 1rem',
                                    borderRadius: '10px',
                                    background: 'rgba(239, 68, 68, 0.1)',
                                    color: 'var(--danger)',
                                    border: '1px solid rgba(239, 68, 68, 0.2)',
                                    cursor: 'pointer',
                                    textAlign: 'left',
                                    fontSize: '0.95rem',
                                    fontWeight: '500',
                                    transition: 'all 0.2s',
                                }}
                            >
                                <LogOut size={18} />
                                Sign Out
                            </button>
                        </div>
                    </div>

                    {/* Content Area */}
                    <div style={{ flex: 1, minWidth: '320px' }}>
                        {activeTab === 'profile' && <ProfileTab />}
                        {activeTab === 'security' && <SecurityTab isUser={type === 'user'} />}
                        {activeTab === 'reporters' && <ReportersTab />}
                        {activeTab === 'billing' && <div className="fade-in"><Subscriptions /></div>}
                        {activeTab === 'preferences' && <PreferencesTab />}
                        {activeTab === 'notifications' && <NotificationsTab />}
                    </div>
                </div>
            </div>

            {/* Inject a small media query for responsiveness manually since we use inline styles primarily */}
            <style>{`
                @media (max-width: 768px) {
                    .settings-layout > div {
                        flex-direction: column;
                    }
                    .glass-panel {
                        width: 100% !important;
                    }
                }
            `}</style>
        </div>
    );
};

export default Settings;
