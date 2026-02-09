import React from 'react';
import { NavLink } from 'react-router-dom';
import { Trophy, Bot, BarChart3, Zap, Lock } from 'lucide-react';
import './Sidebar.css';
import { getAuthUser } from '../../services/authService';

const UserSidebar = () => {
    const user = getAuthUser();
    const displayName = user?.full_name || user?.email || 'User';
    const email = user?.email || '';
    const initials = displayName.substring(0, 2).toUpperCase();

    const navItems = [
        { 
            path: '/user/dashboard', 
            label: 'Winner Products', 
            icon: Trophy, 
            glow: true,
            disabled: true,
            disabledMessage: 'Esta función estará disponible próximamente. Estamos trabajando en traerte los mejores productos ganadores.'
        },
        { 
            path: '/user/reporter-setup', 
            label: 'Configuración Reporter', 
            icon: Bot 
        },
        { 
            path: '/user/analysis', 
            label: 'Análisis de Reportes', 
            icon: BarChart3,
            disabled: true,
            disabledMessage: 'Análisis avanzado disponible próximamente. Podrás ver estadísticas detalladas de tus reportes.'
        },
    ];

    return (
        <aside className="sidebar glass-panel">
            <div className="logo-section">
                <div className="logo-icon">
                    <Zap size={24} color="white" fill="#6366f1" />
                </div>
                <div className="logo-text">
                    <h2>DropTools</h2>
                    <span>Portal de Usuario</span>
                </div>
            </div>

            <nav className="nav-menu">
                {navItems.map((item) => {
                    // Si está deshabilitado, renderizar como div en lugar de NavLink
                    if (item.disabled) {
                        return (
                            <div
                                key={item.path}
                                className="nav-item nav-item-disabled"
                                title={item.disabledMessage}
                                style={{
                                    opacity: 0.5,
                                    cursor: 'not-allowed',
                                    position: 'relative',
                                    pointerEvents: 'none',
                                    filter: 'grayscale(0.3)'
                                }}
                            >
                                <item.icon size={20} />
                                <span>{item.label}</span>
                                
                                {/* Badge "Próximamente" */}
                                <span style={{
                                    position: 'absolute',
                                    top: '8px',
                                    right: '8px',
                                    fontSize: '0.65rem',
                                    fontWeight: 600,
                                    padding: '2px 6px',
                                    borderRadius: '4px',
                                    backgroundColor: 'rgba(245, 158, 11, 0.2)',
                                    color: '#f59e0b',
                                    border: '1px solid rgba(245, 158, 11, 0.3)'
                                }}>
                                    Próximamente
                                </span>
                                
                                {/* Icono de candado */}
                                <Lock 
                                    size={14} 
                                    style={{
                                        position: 'absolute',
                                        bottom: '8px',
                                        right: '8px',
                                        color: 'rgba(245, 158, 11, 0.6)'
                                    }}
                                />
                            </div>
                        );
                    }
                    
                    // Si NO está deshabilitado, renderizar NavLink normal
                    return (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            className={({ isActive }) =>
                                `nav-item ${isActive ? 'active' : ''} ${item.glow ? 'glow-effect' : ''}`
                            }
                        >
                            <item.icon size={20} />
                            <span>{item.label}</span>
                        </NavLink>
                    );
                })}
            </nav>

            <div className="sidebar-footer">
                <div className="user-profile">
                    <div className="avatar" title={email}>{initials}</div>
                    <div className="user-info">
                        <p className="name" title={displayName} style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '140px' }}>
                            {displayName}
                        </p>
                        <p className="role" style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                            {user?.subscription_tier} Plan
                        </p>
                    </div>
                </div>
                <NavLink
                    to="/"
                    className="nav-item logout-btn"
                    style={{ marginTop: '0.5rem', justifyContent: 'center', color: 'var(--danger)', border: '1px solid rgba(239,68,68,0.2)' }}
                    onClick={() => {
                        import('../../services/authService').then(auth => auth.logout());
                    }}
                >
                    <span>Cerrar Sesión</span>
                </NavLink>
            </div>
        </aside>
    );
};

export default UserSidebar;
