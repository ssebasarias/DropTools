import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Trophy, Bot, BarChart3 } from 'lucide-react';
import AppSidebar from './AppSidebar';
import DashboardHeader from './DashboardHeader';
import './MainLayout.css';
import { getAuthUser } from '../../services/authService';
import { hasTier } from '../../utils/subscription';

const UserLayout = () => {
    const location = useLocation();
    const user = getAuthUser();
    const tier = user?.subscription_tier || 'BRONZE';

    // Always show reporter (core feature). Show others only when tier allows.
    const userNavItems = [
        { path: '/user/reporter-setup', label: 'Reporter Setup', icon: Bot, glow: true },
        ...(hasTier(user, 'SILVER') ? [{ path: '/user/analysis', label: 'Report Analysis', icon: BarChart3 }] : []),
        ...(hasTier(user, 'GOLD') ? [{ path: '/user/dashboard', label: 'Winner Products', icon: Trophy }] : []),
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
