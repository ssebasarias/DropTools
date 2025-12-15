import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Pickaxe, Boxes, Server, Settings, Zap } from 'lucide-react';
import './Sidebar.css';

const Sidebar = () => {
    const navItems = [
        { path: '/', label: 'Overview', icon: LayoutDashboard },
        { path: '/gold-mine', label: 'Gold Mine', icon: Pickaxe, glow: true },
        { path: '/cluster-lab', label: 'Cluster Lab', icon: Boxes },
        { path: '/system-status', label: 'System Status', icon: Server },
    ];

    return (
        <aside className="sidebar glass-panel">
            <div className="logo-section">
                <div className="logo-icon">
                    <Zap size={24} color="white" fill="#6366f1" />
                </div>
                <div className="logo-text">
                    <h2>Dahell</h2>
                    <span>Intelligence</span>
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
                <button className="nav-item">
                    <Settings size={20} />
                    <span>Settings</span>
                </button>
                <div className="user-profile">
                    <div className="avatar">AD</div>
                    <div className="user-info">
                        <p className="name">Admin User</p>
                        <p className="role">Superuser</p>
                    </div>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
