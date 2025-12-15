import React, { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, Users, Box, Activity } from 'lucide-react';
import { fetchDashboardStats } from '../services/api';
import './Dashboard.css';

const StatCard = ({ title, value, subtext, icon: Icon, color }) => (
    <div className="glass-card stat-card">
        <div className="stat-header">
            <div className="stat-icon" style={{ backgroundColor: `rgba(${color}, 0.2)`, color: `rgb(${color})` }}>
                <Icon size={22} />
            </div>
            {/* <span className="stat-change positive">+12%</span> */}
        </div>
        <div className="stat-body">
            <h3>{value}</h3>
            <p>{title}</p>
        </div>
    </div>
);

const Dashboard = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadStats = async () => {
            try {
                const data = await fetchDashboardStats();
                setStats(data);
            } catch (error) {
                console.error("Failed to load dashboard stats");
            } finally {
                setLoading(false);
            }
        };
        loadStats();
        // Refresh every 30s
        const interval = setInterval(loadStats, 30000);
        return () => clearInterval(interval);
    }, []);

    if (loading) return <div style={{ padding: '2rem' }}>Loading Neural Core...</div>;
    if (!stats) return <div style={{ padding: '2rem' }}>System Offline. Check Backend Connection.</div>;

    return (
        <div className="dashboard-container">
            <div className="header-greeting">
                <h1>Overview</h1>
                <p>Bienvenido al Centro de Comando, Admin.</p>
            </div>

            {/* Stats Grid */}
            <div className="stats-grid">
                <StatCard title="Total Products" value={stats.total_products?.toLocaleString()} icon={Box} color="99, 102, 241" />
                <StatCard title="Active Clusters" value={stats.active_clusters?.toLocaleString()} icon={Users} color="236, 72, 153" />
                <StatCard title="Vectorized Items" value={stats.vectorized_count?.toLocaleString()} icon={TrendingUp} color="16, 185, 129" />
                <StatCard title="System Status" value={stats.system_status} icon={Activity} color="245, 158, 11" />
            </div>

            {/* Charts Section */}
            <div className="charts-section glass-card">
                <div className="chart-header">
                    <h2>Scraping Activity (Simulated)</h2>
                    <select className="glass-select">
                        <option>Last 7 Days</option>
                    </select>
                </div>
                <div style={{ width: '100%', height: 300 }}>
                    <ResponsiveContainer>
                        <AreaChart data={stats.chart_data}>
                            <defs>
                                <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="name" stroke="#94a3b8" />
                            <YAxis stroke="#94a3b8" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#09090b', borderColor: '#333' }}
                                itemStyle={{ color: '#fff' }}
                            />
                            <Area type="monotone" dataKey="products" stroke="#6366f1" fillOpacity={1} fill="url(#colorProfit)" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div style={{ marginTop: '2rem' }}>
                <p className="text-muted">Conectado a Dahell Intelligence Core v1.0 - {new Date().toLocaleTimeString()}</p>
            </div>
        </div>
    );
};

export default Dashboard;
