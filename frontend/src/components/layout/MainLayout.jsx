import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { LayoutDashboard, Pickaxe, Boxes, Server } from 'lucide-react';
import AppSidebar from './AppSidebar';
import DashboardHeader from './DashboardHeader';
import './MainLayout.css';

const MainLayout = () => {
    const location = useLocation();

    const adminNavItems = [
        { path: '/admin', label: 'Overview', icon: LayoutDashboard, end: true },
        { path: '/admin/gold-mine', label: 'Gold Mine', icon: Pickaxe, glow: true },
        { path: '/admin/cluster-lab', label: 'Cluster Lab', icon: Boxes },
        { path: '/admin/system-status', label: 'System Status', icon: Server },
    ];

    const getPageTitle = () => {
        switch (location.pathname) {
            case '/admin': return 'Dashboard';
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
                title="Dahell"
                subtitle="Intelligence"
                settingsPath="/admin/settings"
                userProfile={{ initials: 'AD', name: 'Admin User', role: 'Superuser' }}
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
