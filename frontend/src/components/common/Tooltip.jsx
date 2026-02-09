import React, { useState } from 'react';
import { Info } from 'lucide-react';

const Tooltip = ({ text, children, position = 'top' }) => {
    const [show, setShow] = useState(false);
    
    const positions = {
        top: { bottom: '100%', left: '50%', transform: 'translateX(-50%)', marginBottom: '8px' },
        bottom: { top: '100%', left: '50%', transform: 'translateX(-50%)', marginTop: '8px' },
        left: { right: '100%', top: '50%', transform: 'translateY(-50%)', marginRight: '8px' },
        right: { left: '100%', top: '50%', transform: 'translateY(-50%)', marginLeft: '8px' },
    };
    
    return (
        <div 
            style={{ position: 'relative', display: 'inline-block' }}
            onMouseEnter={() => setShow(true)}
            onMouseLeave={() => setShow(false)}
        >
            {children || <Info size={16} style={{ color: 'var(--primary)', cursor: 'help' }} />}
            {show && (
                <div style={{
                    position: 'absolute',
                    ...positions[position],
                    background: 'rgba(0, 0, 0, 0.9)',
                    color: 'white',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    whiteSpace: 'nowrap',
                    zIndex: 1000,
                    pointerEvents: 'none',
                    animation: 'fadeIn 0.2s ease-out'
                }}>
                    {text}
                    <div style={{
                        position: 'absolute',
                        ...(position === 'top' && { top: '100%', left: '50%', transform: 'translateX(-50%)', borderTop: '6px solid rgba(0,0,0,0.9)', borderLeft: '6px solid transparent', borderRight: '6px solid transparent' }),
                        ...(position === 'bottom' && { bottom: '100%', left: '50%', transform: 'translateX(-50%)', borderBottom: '6px solid rgba(0,0,0,0.9)', borderLeft: '6px solid transparent', borderRight: '6px solid transparent' }),
                        ...(position === 'left' && { left: '100%', top: '50%', transform: 'translateY(-50%)', borderLeft: '6px solid rgba(0,0,0,0.9)', borderTop: '6px solid transparent', borderBottom: '6px solid transparent' }),
                        ...(position === 'right' && { right: '100%', top: '50%', transform: 'translateY(-50%)', borderRight: '6px solid rgba(0,0,0,0.9)', borderTop: '6px solid transparent', borderBottom: '6px solid transparent' }),
                    }}></div>
                    <style>{`
                        @keyframes fadeIn {
                            from { opacity: 0; transform: ${position === 'top' || position === 'bottom' ? 'translateX(-50%) translateY(-4px)' : position === 'left' ? 'translateY(-50%) translateX(-4px)' : 'translateY(-50%) translateX(4px)'}; }
                            to { opacity: 1; transform: ${position === 'top' || position === 'bottom' ? 'translateX(-50%) translateY(0)' : 'translateY(-50%) translateX(0)'}; }
                        }
                    `}</style>
                </div>
            )}
        </div>
    );
};

export default Tooltip;
