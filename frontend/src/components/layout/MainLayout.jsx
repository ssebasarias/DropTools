import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, Pickaxe, Boxes, Server } from 'lucide-react';
import AppSidebar from './AppSidebar';
import DashboardHeader from './DashboardHeader';
import './MainLayout.css';
import { getAuthUser } from '../../services/authService';

const MainLayout = () => {
    const location = useLocation();
    const user = getAuthUser();

    const adminNavItems = [
        { path: '/admin', label: 'Overview', icon: LayoutDashboard, end: true },
        { path: '/admin/users', label: 'Users & Plans', icon: Users },
        { path: '/admin/gold-mine', label: 'Gold Mine', icon: Pickaxe, glow: true },
        { path: '/admin/cluster-lab', label: 'Cluster Lab', icon: Boxes },
        { path: '/admin/system-status', label: 'System Status', icon: Server },
    ];

    const getPageTitle = () => {
        switch (location.pathname) {
            case '/admin': return 'Dashboard';
            case '/admin/users': return 'Users & Plans';
            case '/admin/gold-mine': return 'Gold Mine';
            case '/admin/cluster-lab': return 'Cluster Analysis';
            case '/admin/system-status': return 'System Control';
            case '/admin/settings': return 'Settings';
            default: return 'Admin Portal';
        }
    };

    return (
        <div className="app-container">
            <AppSidebar
                navItems={adminNavItems}
                title="DropTools"
                subtitle="Intelligence"
                settingsPath="/admin/settings"
                userProfile={{
                    initials: (user?.full_name || user?.email || 'AD').slice(0, 2).toUpperCase(),
                    name: user?.full_name || user?.email || 'Admin',
                    role: 'ADMIN'
                }}
            />
            <main className="main-content">
                <DashboardHeader title={getPageTitle()} />
                <div className="content-scroll">
                    <Outlet />
                </div>
            </main>
        </div>
    );
};

export default MainLayout;
