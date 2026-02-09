import React from 'react';
import { AlertCircle, X } from 'lucide-react';

const ErrorAlert = ({ error, onClose }) => {
    if (!error) return null;
    
    return (
        <div style={{
            padding: '12px 16px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'start',
            gap: '0.75rem',
            animation: 'slideIn 0.3s ease-out'
        }}>
            <AlertCircle size={20} style={{ color: '#ef4444', flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1 }}>
                <p style={{ 
                    margin: 0, 
                    color: '#ef4444', 
                    fontSize: '0.875rem',
                    fontWeight: 500,
                    whiteSpace: 'pre-wrap',
                    maxHeight: '200px',
                    overflow: 'auto'
                }}>
                    {error}
                </p>
            </div>
            {onClose && (
                <button
                    onClick={onClose}
                    style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: '4px',
                        color: '#ef4444',
                        opacity: 0.7,
                        transition: 'opacity 0.2s',
                        flexShrink: 0
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.opacity = 1}
                    onMouseLeave={(e) => e.currentTarget.style.opacity = 0.7}
                >
                    <X size={16} />
                </button>
            )}
        </div>
    );
};

export default ErrorAlert;
