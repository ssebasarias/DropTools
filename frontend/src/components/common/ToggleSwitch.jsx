import React from 'react';

const ToggleSwitch = ({ checked, onChange }) => (
    <div
        onClick={() => onChange && onChange(!checked)}
        style={{
            width: '44px',
            height: '24px',
            background: checked ? 'var(--primary)' : 'rgba(255,255,255,0.1)',
            borderRadius: '99px',
            position: 'relative',
            cursor: 'pointer',
            transition: 'background 0.2s'
        }}>
        <div style={{
            width: '20px',
            height: '20px',
            background: 'white',
            borderRadius: '50%',
            position: 'absolute',
            top: '2px',
            left: checked ? '22px' : '2px',
            transition: 'left 0.2s'
        }} />
    </div>
);

export default ToggleSwitch;
