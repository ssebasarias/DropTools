import React from 'react';
import { NavLink } from 'react-router-dom';
import { Zap, Settings as SettingsIcon, LogOut } from 'lucide-react';
import './Sidebar.css';
import { logout } from '../../services/authService';

const AppSidebar = ({
    navItems,
    title = "Dahell",
    subtitle = "Intelligence",
    settingsPath = "/settings",
    userProfile = { initials: 'U', name: 'User', role: 'Guest' }
}) => {
    return (
        <aside className="sidebar glass-panel">
            <div className="logo-section">
                <div className="logo-icon">
                    <Zap size={24} color="white" fill="#6366f1" />
                </div>
                <div className="logo-text">
                    <h2>{title}</h2>
                    <span>{subtitle}</span>
                </div>
            </div>

            <nav className="nav-menu">
                {navItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) =>
                            `nav-item ${isActive ? 'active' : ''} ${item.glow ? 'glow-effect' : ''}`
                        }
                        end={item.end}
                    >
                        <item.icon size={20} />
                        <span>{item.label}</span>
                    </NavLink>
                ))}
            </nav>

            <div className="sidebar-footer">
                <NavLink
                    to={settingsPath}
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    style={{ justifyContent: 'flex-start', border: 'none' }}
                >
                    <SettingsIcon size={20} />
                    <span>Settings</span>
                </NavLink>
                <button
                    type="button"
                    onClick={logout}
                    className="nav-item"
                    style={{
                        justifyContent: 'flex-start',
                        border: 'none',
                        width: '100%',
                        background: 'transparent',
                        cursor: 'pointer',
                        color: 'var(--danger)',
                    }}
                >
                    <LogOut size={20} />
                    <span>Logout</span>
                </button>
                <div className="user-profile">
                    <div className="avatar">{userProfile.initials}</div>
                    <div className="user-info">
                        <p className="name">{userProfile.name}</p>
                        <p className="role">{userProfile.role}</p>
                    </div>
                </div>
            </div>
        </aside>
    );
};

export default AppSidebar;
