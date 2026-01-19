import React from 'react';
import ThemeToggle from '../ThemeToggle';

const DashboardHeader = ({ title, breadcrumbRoot = "Dahell" }) => {
    return (
        <header className="top-header glass-panel-flat">
            <div className="breadcrumbs">
                <span>{breadcrumbRoot}</span> / <span className="current-page">{title}</span>
            </div>
            <div className="header-actions">
                <ThemeToggle />
            </div>
        </header>
    );
};

export default DashboardHeader;
