import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Trophy, Bot, BarChart3 } from 'lucide-react';
import AppSidebar from './AppSidebar';
import DashboardHeader from './DashboardHeader';
import './MainLayout.css';

const UserLayout = () => {
    const location = useLocation();

    const userNavItems = [
        { path: '/user/dashboard', label: 'Winner Products', icon: Trophy, glow: true },
        { path: '/user/reporter-setup', label: 'Reporter Setup', icon: Bot },
        { path: '/user/analysis', label: 'Report Analysis', icon: BarChart3 },
    ];

    const getPageTitle = () => {
        switch (location.pathname) {
            case '/user/dashboard': return 'Winner Products';
            case '/user/reporter-setup': return 'Reporter Configuration';
            case '/user/analysis': return 'Analysis Dashboard';
            case '/user/settings': return 'Settings';
            default: return 'User Portal';
        }
    };

    return (
        <div className="app-container">
            <AppSidebar
                navItems={userNavItems}
                title="Dahell"
                subtitle="User Portal"
                settingsPath="/user/settings"
                userProfile={{ initials: 'JD', name: 'John Doe', role: 'Standard User' }}
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

export default UserLayout;
