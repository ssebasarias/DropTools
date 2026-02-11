import React from 'react';

const GlassCard = ({ children, className = '', style = {}, padding = '1.25rem', hoverEffect = false, onClick }) => {
    const baseStyle = {
        background: 'rgba(255, 255, 255, 0.03)',
        backdropFilter: 'blur(10px)',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        padding: padding,
        ...style
    };

    const handleMouseEnter = (e) => {
        if (hoverEffect) {
            e.currentTarget.style.transform = 'translateY(-4px)';
            e.currentTarget.style.boxShadow = '0 10px 20px rgba(0,0,0,0.3)';
            e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.5)';
        }
    };

    const handleMouseLeave = (e) => {
        if (hoverEffect) {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.05)';
        }
    };

    return (
        <div
            className={`glass-card-component ${className}`}
            style={baseStyle}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            onClick={onClick}
        >
            {children}
            <style>{`
                .glass-card-component {
                    transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
                }
            `}</style>
        </div>
    );
};

export default GlassCard;
