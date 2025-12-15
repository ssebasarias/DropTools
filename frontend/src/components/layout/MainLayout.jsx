import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import './MainLayout.css';

const MainLayout = () => {
    return (
        <div className="app-container">
            <Sidebar />
            <main className="main-content">
                <header className="top-header glass-panel-flat">
                    <div className="breadcrumbs">
                        <span>Dahell</span> / <span className="current-page">Dashboard</span>
                    </div>
                </header>
                <div className="content-scroll">
                    <Outlet />
                </div>
            </main>
        </div>
    );
};

export default MainLayout;
