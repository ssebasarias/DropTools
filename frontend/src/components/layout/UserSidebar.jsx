import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Trophy, Bot, BarChart3, LogOut, Zap, Settings as SettingsIcon, CreditCard } from 'lucide-react';
import './Sidebar.css';

const UserSidebar = () => {
    const navigate = useNavigate();

    const navItems = [
        { path: '/user/dashboard', label: 'Winner Products', icon: Trophy, glow: true },
        { path: '/user/reporter-setup', label: 'Reporter Setup', icon: Bot },
        { path: '/user/analysis', label: 'Report Analysis', icon: BarChart3 },
    ];

    const handleLogout = () => {
        navigate('/login');
    };

    return (
        <aside className="sidebar glass-panel">
            <div className="logo-section">
                <div className="logo-icon">
                    <Zap size={24} color="white" fill="#6366f1" />
                </div>
                <div className="logo-text">
                    <h2>Dahell</h2>
                    <span>User Portal</span>
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
                    >
                        <item.icon size={20} />
                        <span>{item.label}</span>
                    </NavLink>
                ))}
            </nav>

            <div className="sidebar-footer">
                <NavLink
                    to="/user/settings"
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    style={{ justifyContent: 'flex-start', border: 'none' }}
                >
                    <SettingsIcon size={20} />
                    <span>Settings</span>
                </NavLink>
                <div className="user-profile">
                    <div className="avatar">JD</div>
                    <div className="user-info">
                        <p className="name">John Doe</p>
                        <p className="role">Standard User</p>
                    </div>
                </div>
            </div>
        </aside>
    );
};

export default UserSidebar;
