import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Trophy, Bot, BarChart3 } from 'lucide-react';
import AppSidebar from './AppSidebar';
import DashboardHeader from './DashboardHeader';
import './MainLayout.css';
import { getAuthUser } from '../../services/authService';

const UserLayout = () => {
    const location = useLocation();
    const user = getAuthUser();
    const tier = (user?.subscription_tier || 'BRONZE').toUpperCase();

    const userNavItems = [
        { path: '/user/winner-products', label: 'Productos ganadores', icon: Trophy, glow: false },
        { path: '/user/reporter-setup', label: 'Report CAS', icon: Bot, glow: true },
        { path: '/user/analytics', label: 'Analytics', icon: BarChart3, glow: false },
    ];

    const getPageTitle = () => {
        switch (location.pathname) {
            case '/user/analytics': return 'Analytics';
            case '/user/winner-products': return 'Productos ganadores';
            case '/user/reporter-setup': return 'Report CAS';
            case '/user/settings': return 'Settings';
            default: return 'User Portal';
        }
    };

    return (
        <div className="app-container">
            <AppSidebar
                navItems={userNavItems}
                title="DropTools"
                subtitle="User Portal"
                settingsPath="/user/settings"
                userProfile={{
                    initials: (user?.full_name || user?.email || 'U').slice(0, 2).toUpperCase(),
                    name: user?.full_name || user?.email || 'User',
                    role: `${tier} Plan`
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

export default UserLayout;



