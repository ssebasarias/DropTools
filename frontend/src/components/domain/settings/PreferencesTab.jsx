import React from 'react';
import ToggleSwitch from '../../common/ToggleSwitch';

const PreferencesTab = () => (
    <div className="glass-card fade-in">
        <h3 style={{ marginBottom: '1.5rem', fontSize: '1.25rem', fontWeight: '600' }}>Preferences</h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h4 style={{ fontWeight: '500', marginBottom: '0.25rem' }}>Email Notifications</h4>
                    <p className="text-muted" style={{ fontSize: '0.9rem' }}>Receive reports and alerts via email.</p>
                </div>
                <ToggleSwitch checked={true} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h4 style={{ fontWeight: '500', marginBottom: '0.25rem' }}>Winner Product Alerts</h4>
                    <p className="text-muted" style={{ fontSize: '0.9rem' }}>Get notified instantly when a new high-potential product is found.</p>
                </div>
                <ToggleSwitch checked={true} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '1.5rem', borderTop: '1px solid var(--glass-border)' }}>
                <div>
                    <h4 style={{ fontWeight: '500', marginBottom: '0.25rem' }}>Eye Protection Mode</h4>
                    <p className="text-muted" style={{ fontSize: '0.9rem' }}>Reduce blue light automatically after sunset.</p>
                </div>
                <ToggleSwitch checked={false} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h4 style={{ fontWeight: '500', marginBottom: '0.25rem' }}>Compact Density</h4>
                    <p className="text-muted" style={{ fontSize: '0.9rem' }}>Show more data on screen by reducing padding.</p>
                </div>
                <ToggleSwitch checked={false} />
            </div>
        </div>
    </div>
);

export default PreferencesTab;
